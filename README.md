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

The preparation helper is:

```text
raw2ready.py
```

It converts fetched raw JSON rows into relational tables for downstream
analysis.

## Setup

Create `.env` from the example:

```bash
cp .env.example .env
```

Then edit `.env`:

```bash
MOLTBOOK_API_KEY=your_real_key_here
```

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
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
output/raw.db
```

The CSV is the input list of post IDs. The SQLite database is the local output
file where fetched posts, fetched comments, and progress status are stored.
If the output database already exists, the script continues from its existing
`fetch_status` and appends newly fetched rows. Existing rows are not
overwritten.

```text
examples/post_ids.csv          # sample input committed to Git
output/raw.db                  # local output ignored by Git
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

## Prepare Analysis Database

After fetching both posts and comments, build the analysis-ready SQLite
database:

```bash
python3 raw2ready.py
```

The fetched database must contain both `posts` and `comments` rows. If you
previously fetched only comments, fetch posts before preparing the analysis
database:

```bash
python3 fetch_moltbook.py --fetch posts
```

By default, this reads:

```text
output/raw.db
```

and writes:

```text
output/ready.db
```

You can override both paths:

```bash
python3 raw2ready.py \
  --raw-db output/raw.db \
  --ready-db output/ready.db
```

`output/ready.db` is the file used by `moltbook-post-analysis` and the file to
publish with the analysis dataset.

## Reset Local Data

The database stores both fetched data and fetch progress. If you want to rerun
everything from the beginning, remove the local database:

```bash
rm output/raw.db
```

The next run will create a fresh database and fetch all post IDs again.

## Git Notes

Commit these:

```text
fetch_moltbook.py
raw2ready.py
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
