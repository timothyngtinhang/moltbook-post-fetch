# Moltbook Post Fetch

One clear script for fetching Moltbook posts and comments into a local SQLite
database.

When you run the script, it reads post IDs from a CSV file, calls the Moltbook
API for each post, and saves the returned post/comment data into SQLite. It also
keeps a small `fetch_status` table so the job can pick up where it left off
instead of starting over every time.

The main file is:

```text
fetch_moltbook.py
```

Read that file from top to bottom. It is organized in the same order the program runs:

```text
main()
argument parsing
.env loading
CSV reading
Moltbook API client
SQLite database
fetch loops
```

## Setup

Create `.env` from the example:

```bash
cp .env.example .env
```

Then edit `.env`:

```bash
MOLTBOOK_API_KEY=your_real_key_here
```

Install dependencies if your machine has `pip`:

```bash
python3 -m pip install -r requirements.txt
```

## Run

Fetch both posts and comments:

```bash
python3 fetch_moltbook.py
```

Fetch only comments:

```bash
python3 fetch_moltbook.py --fetch comments
```

Fetch only posts:

```bash
python3 fetch_moltbook.py --fetch posts
```

By default, the script uses:

```text
examples/post_ids.csv
output/moltbook_fetched.db
```

The CSV is the input list of post IDs. The SQLite database is the local output
file where fetched posts, fetched comments, and progress status are stored.

```text
examples/post_ids.csv          # sample input committed to Git
output/moltbook_fetched.db     # local output ignored by Git
```

You can override those paths:

```bash
python3 fetch_moltbook.py --csv path/to/post_ids.csv --db output/custom_fetch.db
```

This is useful if you want to test on a smaller CSV or write to a temporary
database first:

```bash
python3 fetch_moltbook.py --csv examples/post_ids.csv --db output/test_fetch.db
```

## Reset Local Data

The database stores both fetched data and fetch progress. If you want to rerun
everything from the beginning, remove the local database:

```bash
rm output/moltbook_fetched.db
```

The next run will create a fresh database and fetch all post IDs again.

## Git Notes

Commit these:

```text
fetch_moltbook.py
requirements.txt
README.md
.env.example
.gitignore
examples/post_ids.csv
output/.gitkeep
```

Do not commit these:

```text
.env
output/*.db
output/*.db-*
nohup.out
```
