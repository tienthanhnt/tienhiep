-- Optional manual ordering for books.
-- Lower ranking appears first. Null ranking falls back to id order.
-- Safe to run multiple times in Supabase SQL Editor.

ALTER TABLE books
ADD COLUMN IF NOT EXISTS ranking INTEGER;

CREATE INDEX IF NOT EXISTS idx_books_ranking_id
ON books (ranking ASC NULLS LAST, id ASC);

