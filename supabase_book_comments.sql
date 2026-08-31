-- Reader comments for books.
-- Safe to run multiple times in Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS book_comments (
  id BIGSERIAL PRIMARY KEY,
  book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  chapter_number INTEGER,
  nickname TEXT NOT NULL CHECK (char_length(nickname) BETWEEN 2 AND 40),
  content TEXT NOT NULL CHECK (char_length(content) BETWEEN 3 AND 1000),
  rating SMALLINT CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
  visitor_hash TEXT NOT NULL,
  user_agent_hash TEXT,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT TIMEZONE('utc'::text, NOW())
);

CREATE INDEX IF NOT EXISTS idx_book_comments_book_created
ON book_comments (book_id, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_book_comments_visitor_created
ON book_comments (visitor_hash, created_at DESC);

ALTER TABLE book_comments ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION list_book_comments(
  target_book_id INTEGER,
  max_rows INTEGER DEFAULT 60
)
RETURNS TABLE (
  id BIGINT,
  book_id INTEGER,
  chapter_number INTEGER,
  nickname TEXT,
  content TEXT,
  rating SMALLINT,
  created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    c.id,
    c.book_id,
    c.chapter_number,
    c.nickname,
    c.content,
    c.rating,
    c.created_at
  FROM book_comments c
  WHERE c.book_id = target_book_id
  ORDER BY c.created_at DESC, c.id DESC
  LIMIT LEAST(GREATEST(max_rows, 1), 60);
$$;

CREATE OR REPLACE FUNCTION create_book_comment(
  target_book_id INTEGER,
  target_chapter_number INTEGER,
  target_nickname TEXT,
  target_content TEXT,
  target_rating SMALLINT,
  target_visitor_hash TEXT,
  target_user_agent_hash TEXT DEFAULT NULL
)
RETURNS TABLE (
  id BIGINT,
  book_id INTEGER,
  chapter_number INTEGER,
  nickname TEXT,
  content TEXT,
  rating SMALLINT,
  created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  inserted_id BIGINT;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM books WHERE books.id = target_book_id) THEN
    RAISE EXCEPTION 'BOOK_NOT_FOUND';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM book_comments c
    WHERE c.visitor_hash = target_visitor_hash
      AND c.created_at > TIMEZONE('utc'::text, NOW()) - INTERVAL '2 minutes'
    LIMIT 1
  ) THEN
    RAISE EXCEPTION 'COMMENT_GLOBAL_COOLDOWN';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM book_comments c
    WHERE c.book_id = target_book_id
      AND c.visitor_hash = target_visitor_hash
      AND c.created_at > TIMEZONE('utc'::text, NOW()) - INTERVAL '10 minutes'
    LIMIT 1
  ) THEN
    RAISE EXCEPTION 'COMMENT_BOOK_COOLDOWN';
  END IF;

  INSERT INTO book_comments (
    book_id,
    chapter_number,
    nickname,
    content,
    rating,
    visitor_hash,
    user_agent_hash
  )
  VALUES (
    target_book_id,
    target_chapter_number,
    btrim(target_nickname),
    btrim(target_content),
    target_rating,
    target_visitor_hash,
    target_user_agent_hash
  )
  RETURNING book_comments.id INTO inserted_id;

  DELETE FROM book_comments c
  WHERE c.book_id = target_book_id
    AND c.id IN (
      SELECT old_comments.id
      FROM book_comments old_comments
      WHERE old_comments.book_id = target_book_id
      ORDER BY old_comments.created_at DESC, old_comments.id DESC
      OFFSET 60
    );

  RETURN QUERY
  SELECT
    c.id,
    c.book_id,
    c.chapter_number,
    c.nickname,
    c.content,
    c.rating,
    c.created_at
  FROM book_comments c
  WHERE c.id = inserted_id;
END;
$$;

GRANT EXECUTE ON FUNCTION list_book_comments(INTEGER, INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION list_book_comments(INTEGER, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION create_book_comment(INTEGER, INTEGER, TEXT, TEXT, SMALLINT, TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION create_book_comment(INTEGER, INTEGER, TEXT, TEXT, SMALLINT, TEXT, TEXT) TO authenticated;
