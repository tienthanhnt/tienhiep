#!/usr/bin/env python3
from dotenv import load_dotenv

from cloudflare_store import d1_query, d1_rows


load_dotenv()


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      public_id TEXT UNIQUE,
      title TEXT NOT NULL UNIQUE,
      author TEXT NOT NULL DEFAULT 'Chưa rõ',
      status TEXT NOT NULL DEFAULT 'Đang ra',
      description TEXT NOT NULL DEFAULT '',
      genres TEXT NOT NULL DEFAULT '',
      source_type TEXT NOT NULL DEFAULT '',
      ranking INTEGER NOT NULL DEFAULT 0,
      rating REAL NOT NULL DEFAULT 8.0,
      chapter_count INTEGER NOT NULL DEFAULT 0,
      cover_url TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chapters (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      book_id INTEGER NOT NULL,
      chapter_number INTEGER NOT NULL,
      title TEXT NOT NULL,
      content_html TEXT NOT NULL DEFAULT '',
      content_path TEXT NOT NULL DEFAULT '',
      content_url TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(book_id, chapter_number),
      FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_books_ranking_id ON books(ranking DESC, id DESC)",
    "CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)",
    "CREATE INDEX IF NOT EXISTS idx_chapters_book_number ON chapters(book_id, chapter_number)",
]


def main() -> int:
    print("🔧 Đang tạo schema D1 cho nguồn truyện mới...")
    for statement in SCHEMA_STATEMENTS:
        d1_query(statement)

    tables = d1_rows(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('books', 'chapters') ORDER BY name"
    )
    table_names = ", ".join(row["name"] for row in tables)
    print(f"✅ Schema OK. Tables: {table_names}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
