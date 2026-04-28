import argparse
import csv
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CSV = PROJECT_ROOT / "examples/post_ids.csv"
DEFAULT_DB = PROJECT_ROOT / "output/moltbook_fetched.db"
DEFAULT_ENV = PROJECT_ROOT / ".env"

BASE_URL = "https://moltbook.com/api/v1/"
DEFAULT_RATE_PER_MINUTE = 50
REQUEST_TIMEOUT = (5, 30)

SERVER_RETRY_WAIT_SECONDS = 60 * 5       # 5 minutes 
SERVER_RETRY_MAX_SECONDS = 24 * 60 * 60  # 1 day


def main() -> None:
    args = parse_args()
    setup_logging()

    load_dotenv()
    api_key = os.environ["MOLTBOOK_API_KEY"]
    post_ids = read_post_ids(args.csv)

    client = MoltbookClient(api_key, rate_per_minute=args.rate)
    db = MoltbookDatabase(args.db)

    try:
        db.initialize_fetch_status(post_ids)

        if args.fetch in {"comments", "both"}:
            fetch_comments(client, db)

        if args.fetch in {"posts", "both"}:
            fetch_posts(client, db)
    finally:
        db.close()

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Moltbook posts/comments into SQLite."
    )
    parser.add_argument(
        "--fetch",
        choices=["comments", "posts", "both"],
        default="both",
        help="Choose what to fetch. Default: both.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help="CSV of post IDs. Default: examples/post_ids.csv.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help="SQLite DB path. Default: output/moltbook_fetched.db.",
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=DEFAULT_RATE_PER_MINUTE,
        help="Requests per minute. Default: 50.",
    )
    return parser.parse_args()


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

def read_post_ids(csv_path: Path) -> list[str]:
    with csv_path.open(newline="") as f:
        reader = csv.reader(f)
        return [row[0].strip() for row in reader if row]

class MoltbookClient:
    def __init__(self, api_key: str, rate_per_minute: int) -> None:
        self.rate_per_minute = rate_per_minute
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            backoff_jitter=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)

    def fetch_json(self, url: str) -> dict:
        server_dead_count = 0
        while True:
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                time.sleep(60 / self.rate_per_minute)
                return response.json()
            except requests.RequestException as e:
                logging.error("Request failed for %s: %s", url, e)
                server_dead_count += 1
                time.sleep(SERVER_RETRY_WAIT_SECONDS)
                if server_dead_count * SERVER_RETRY_WAIT_SECONDS > SERVER_RETRY_MAX_SECONDS:
                    raise RuntimeError(
                        f"Server seems unresponsive after 1 day. Abort"
                    )

    def get_post(self, post_id: str) -> dict:
        return self.fetch_json(f"{BASE_URL}posts/{post_id}")

    def get_comment_batches(self, post_id: str):
        url = f"{BASE_URL}posts/{post_id}/comments"

        while True:
            data = self.fetch_json(url)
            has_more = bool(data.get("has_more"))
            cursor = data.get("next_cursor")

            yield data, has_more

            if not has_more:
                break
            if not cursor:
                raise ValueError(f"Missing next_cursor for post {post_id}")

            url = f"{BASE_URL}posts/{post_id}/comments/?cursor={cursor}"


class MoltbookDatabase:
    def __init__(self, db_path: Path) -> None:
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self) -> None:
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS comments (
                comment_id TEXT PRIMARY KEY,
                post_id TEXT,
                fetch_at TIMESTAMP,
                raw_data JSON
            );
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                post_id TEXT PRIMARY KEY,
                fetch_at TIMESTAMP,
                raw_data JSON
            );
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fetch_status (
                post_id TEXT PRIMARY KEY,
                post_fetched INTEGER NOT NULL DEFAULT 0,
                comment_fetched INTEGER NOT NULL DEFAULT 0
            ) WITHOUT ROWID;
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_incomplete_posts
            ON fetch_status (post_id)
            WHERE post_fetched = 0;
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_incomplete_comments
            ON fetch_status (post_id)
            WHERE comment_fetched = 0;
            """
        )
        self.conn.commit()

    def initialize_fetch_status(self, post_ids: list[str]) -> None:
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO fetch_status
                (post_id, post_fetched, comment_fetched)
            VALUES (?, 0, 0);
            """,
            [(post_id,) for post_id in post_ids],
        )
        self.conn.commit()

    def get_next_post_id(self, status_column: str) -> str | None:
        if status_column not in {"post_fetched", "comment_fetched"}:
            raise ValueError(f"Unexpected status column: {status_column}")
        
        row = self.conn.execute(
            f"SELECT post_id FROM fetch_status WHERE {status_column} = 0 LIMIT 1"
        ).fetchone()
        return row[0] if row else None

    def mark_complete(self, post_id: str, status_column: str) -> None:
        if status_column not in {"post_fetched", "comment_fetched"}:
            raise ValueError(f"Unexpected status column: {status_column}")
        
        self.conn.execute(
            f"UPDATE fetch_status SET {status_column} = 1 WHERE post_id = ?",
            (post_id,),
        )
        self.conn.commit()

    def save_post(self, api_response: dict) -> None:
        post = api_response.get("post", api_response)
        post_id = post.get("id")
        if not post_id:
            raise ValueError(f"Post response did not include an id: {api_response}")

        self.conn.execute(
            "INSERT OR IGNORE INTO posts VALUES (?, ?, ?)",
            (post_id, utc_now(), json.dumps(api_response)),
        )
        self.conn.commit()

    def save_comments(self, api_response: dict) -> int:
        comments = api_response.get("comments", [])
        rows = [
            {
                "comment_id": comment.get("id"),
                "post_id": comment.get("post_id"),
                "fetch_at": utc_now(),
                "raw_data": json.dumps(comment),
            }
            for comment in comments
            if comment.get("id")
        ]

        self.conn.executemany(
            """
            INSERT OR IGNORE INTO comments
                (comment_id, post_id, fetch_at, raw_data)
            VALUES (:comment_id, :post_id, :fetch_at, :raw_data)
            """,
            rows,
        )
        self.conn.commit()
        return len(rows)

    def close(self) -> None:
        self.conn.close()


def fetch_comments(client: MoltbookClient, db: MoltbookDatabase) -> None:
    while True:
        post_id = db.get_next_post_id("comment_fetched")
        if post_id is None:
            logging.info("No more comments to fetch.")
            return

        logging.info("Fetching comments for post %s", post_id)
        for batch_number, (data, has_more) in enumerate(
            client.get_comment_batches(post_id),
            start=1,
        ):
            saved_count = db.save_comments(data)
            logging.info(
                "Saved %s comments for post %s from batch %s; has_more=%s",
                saved_count,
                post_id,
                batch_number,
                has_more,
            )

        db.mark_complete(post_id, "comment_fetched")


def fetch_posts(client: MoltbookClient, db: MoltbookDatabase) -> None:
    while True:
        post_id = db.get_next_post_id("post_fetched")
        if post_id is None:
            logging.info("No more posts to fetch.")
            return

        logging.info("Fetching post %s", post_id)
        db.save_post(client.get_post(post_id))
        db.mark_complete(post_id, "post_fetched")

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
