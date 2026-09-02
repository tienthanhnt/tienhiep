#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from cloudflare_store import d1_rows
from supabase_lookup import fetch_supabase_title_slugs, slugify


load_dotenv()

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "chapters"
BATCH_MANIFEST_FILE = ".batch_epub_upload_latest.json"


def read_info_value(book_dir: Path, key_name: str) -> str:
    info_path = book_dir / "book_info.txt"
    if not info_path.exists():
        return ""

    for line in info_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == key_name:
            return value.strip()
    return ""


def read_manifest(output_dir: Path) -> list[Path]:
    manifest_path = output_dir / BATCH_MANIFEST_FILE
    if not manifest_path.exists():
        print(f"❌ Không tìm thấy manifest: {manifest_path}")
        sys.exit(1)

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [Path(path).expanduser().resolve() for path in data.get("book_dirs", [])]


def count_md_files(book_dir: Path) -> int:
    if not book_dir.is_dir():
        return 0
    return sum(1 for path in book_dir.iterdir() if path.is_file() and path.suffix.lower() == ".md")


def fetch_d1_books() -> dict[str, dict]:
    rows = d1_rows(
        """
        SELECT id, public_id, title, chapter_count
        FROM books
        ORDER BY id ASC
        """
    )
    return {slugify(row.get("title") or ""): row for row in rows if row.get("title")}


def format_match(row: dict | None, source: str) -> str:
    if not row:
        return "-"
    public_id = row.get("public_id") or row.get("id")
    chapter_count = row.get("chapter_count") or 0
    return f"{source}:{public_id} ({chapter_count} ch)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Kiểm tra batch EPUB mới đã upload vào D1/R2 hay trùng Supabase chưa.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Folder chứa .batch_epub_upload_latest.json. Mặc định: importer/chapters",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    book_dirs = read_manifest(output_dir)
    print(f"🔎 Batch manifest: {output_dir / BATCH_MANIFEST_FILE}")
    print(f"📚 Số folder trong batch: {len(book_dirs)}")
    print("🔎 Đang đọc D1 và Supabase để đối chiếu...")

    d1_books = fetch_d1_books()
    supabase_books = fetch_supabase_title_slugs()

    uploaded_d1 = 0
    exists_supabase = 0
    missing_d1 = 0
    overlap = 0

    print()
    print(f"{'#':>2}  {'status':<22} {'local':>6}  {'D1/R2':<18} {'Supabase':<18} title")
    print("-" * 120)

    for index, book_dir in enumerate(book_dirs, 1):
        title = read_info_value(book_dir, "title") or book_dir.name.removesuffix("_Translated").replace("_", " ")
        local_count = count_md_files(book_dir)
        key = slugify(title)
        d1_book = d1_books.get(key)
        supabase_book = supabase_books.get(key)

        if d1_book:
            uploaded_d1 += 1
        else:
            missing_d1 += 1
        if supabase_book:
            exists_supabase += 1
        if d1_book and supabase_book:
            overlap += 1

        if d1_book and supabase_book:
            status = "D1+SUPABASE_DUP"
        elif d1_book:
            status = "UPLOADED_D1"
        elif supabase_book:
            status = "EXISTS_SUPABASE"
        else:
            status = "NOT_UPLOADED"

        print(
            f"{index:>2}  {status:<22} {local_count:>6}  "
            f"{format_match(d1_book, 'D1'):<18} {format_match(supabase_book, 'SB'):<18} {title}"
        )

    print("-" * 120)
    print(f"✅ Đã upload vào D1/R2 : {uploaded_d1}/{len(book_dirs)}")
    print(f"⚠️  Đã có trong Supabase : {exists_supabase}/{len(book_dirs)}")
    print(f"❌ Chưa upload vào D1/R2: {missing_d1}/{len(book_dirs)}")
    if overlap:
        print(f"⚠️  Trùng cả D1 và Supabase: {overlap}/{len(book_dirs)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
