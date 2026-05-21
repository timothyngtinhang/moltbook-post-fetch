# Moltbook Post Fetch

A small, reproducible workflow for fetching the latest available Moltbook post and comment data from a known list of post IDs, storing raw API responses in SQLite, and preparing cleaned relational tables for downstream analysis.

## Why this repo exists

Moltbook post and comment data can change depending on when the API is queried. Posts may continue receiving comments after they first appear, so a dataset collected at one point in time may not contain the same post-comment state as a later API fetch.

This repo provides a simple local workflow for re-fetching Moltbook posts and comments from a known list of post IDs. It stores the raw API responses in SQLite and keeps a `fetch_status` table so fetching can be resumed, audited, and reproduced more easily.

The workflow is designed around two steps:

1. Fetch the latest available post/comment API responses into `output/raw.db`
2. Convert the raw database into an analysis-ready SQLite database, `output/ready.db`

If you need a source list of Moltbook post IDs, refer to [`moltbook-observatory-archive`](https://huggingface.co/datasets/SimulaMet/moltbook-observatory-archive). This repo assumes that you already have a CSV of post IDs and focuses on fetching the corresponding post/comment data from the live API.

## Database outputs

`fetch_moltbook.py` creates `output/raw.db` with:

- `posts`: raw post API responses
- `comments`: raw comment API responses
- `fetch_status`: progress tracking for resumable fetching

`raw2ready.py` creates `output/ready.db` with cleaned relational tables for analysis.

## Main files

```text

fetch_moltbook.py   # fetch posts/comments from the Moltbook API into raw.db

raw2ready.py        # convert raw.db into cleaned relational tables in ready.db
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

The fetched database should contain both `posts` and `comments` rows. If you
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
