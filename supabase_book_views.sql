-- Lightweight per-book view counter.
-- Safe to run multiple times in Supabase SQL Editor.

ALTER TABLE books
ADD COLUMN IF NOT EXISTS view_count BIGINT NOT NULL DEFAULT 0;

CREATE OR REPLACE FUNCTION increment_book_view(target_book_id INTEGER)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  next_count BIGINT;
BEGIN
  UPDATE books
  SET view_count = COALESCE(view_count, 0) + 1
  WHERE id = target_book_id
  RETURNING view_count INTO next_count;

  RETURN COALESCE(next_count, 0);
END;
$$;

GRANT EXECUTE ON FUNCTION increment_book_view(INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION increment_book_view(INTEGER) TO authenticated;

