import os
import re
import unicodedata
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SUPABASE_PAGE_SIZE = 1000


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "").replace("Đ", "D").replace("đ", "d")
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", without_marks.lower()).strip("-")


def fetch_supabase_title_slugs() -> dict[str, dict]:
    try:
        from dotenv import load_dotenv
        from supabase import create_client

        load_dotenv(SCRIPT_DIR / ".env")
    except Exception as exc:
        print(f"⚠️  Không load được Supabase SDK/env để kiểm tra trùng: {exc}")
        return {}

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("⚠️  Thiếu SUPABASE_URL/SUPABASE_KEY, bỏ qua kiểm tra trùng Supabase.")
        return {}

    try:
        supabase = create_client(url, key)
        books: dict[str, dict] = {}
        for start in range(0, 100000, SUPABASE_PAGE_SIZE):
            end = start + SUPABASE_PAGE_SIZE - 1
            result = (
                supabase.table("books")
                .select("id,title,chapter_count")
                .order("id")
                .range(start, end)
                .execute()
            )
            rows = result.data or []
            for row in rows:
                title = row.get("title")
                if title:
                    books[slugify(title)] = row
            if len(rows) < SUPABASE_PAGE_SIZE:
                break
        return books
    except Exception as exc:
        print(f"⚠️  Không kiểm tra được Supabase, bỏ qua chống trùng Supabase: {exc}")
        return {}


def find_supabase_book_by_title(title: str) -> dict | None:
    return fetch_supabase_title_slugs().get(slugify(title))
