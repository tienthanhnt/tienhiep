-- Add lightweight SEO metadata for books.
-- Safe to run multiple times in Supabase SQL Editor.

ALTER TABLE books ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE books ADD COLUMN IF NOT EXISTS genres TEXT;
ALTER TABLE books ADD COLUMN IF NOT EXISTS source_type TEXT;

