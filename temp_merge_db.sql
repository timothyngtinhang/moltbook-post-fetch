-- Helper for combining separate post/comment fetch databases into one raw DB.
-- Run from the repository root with:
--
--   sqlite3 output/raw.db < temp_merge_db.sql
--
-- Adjust the attached paths if your split databases live somewhere else.

ATTACH 'output/posts.db' AS posts_db;
ATTACH 'output/comments.db' AS comments_db;

CREATE TABLE IF NOT EXISTS posts (
            post_id TEXT PRIMARY KEY,
            fetch_at TIMESTAMP,
            raw_data JSON
        ); 

INSERT OR IGNORE INTO posts
SELECT *
FROM posts_db.posts;

CREATE TABLE IF NOT EXISTS comments (
            comment_id TEXT PRIMARY KEY,
            post_id TEXT,
            fetch_at TIMESTAMP,
            raw_data JSON
        );

INSERT OR IGNORE INTO comments
SELECT *
FROM comments_db.comments;
