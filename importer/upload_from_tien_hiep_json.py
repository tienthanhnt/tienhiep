"""
Convert and upload books from importer/tien_hiep/all_tien_hiep.json.

Default behavior:
  - sort by ranking asc
  - skip duplicate=true
  - skip uploaded=true
  - skip repeated titles within the JSON batch
  - convert EPUB to chapters/
  - write book_info.txt from JSON metadata
  - upload with upload_translated.py logic
  - mark uploaded=true after the book appears in Supabase

Useful safer modes:
  --convert-only  Convert EPUB files and write book_info.txt, but do not upload.
  --upload-only   Upload already-converted folders, but do not convert EPUB files.
  --offset N      Skip the first N eligible books before selecting --count books.
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

import epub_to_md
import upload_translated


DEFAULT_JSON_PATH = Path(__file__).resolve().parent / "tien_hiep" / "all_tien_hiep.json"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "chapters"


def clean_book_title(value: str) -> str:
    value = value or ""
    value = re.sub(r"^\s*\[[^\]]+\]\s*", "", value, flags=re.I)
    value = re.sub(r"^\s*\([^\)]+\)\s*", "", value, flags=re.I)
    value = re.sub(r"\s*-\s*sưu\s*tầm\s*$", "", value, flags=re.I)
    value = re.sub(r"\s*-\s*suu\s*tam\s*$", "", value, flags=re.I)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" -_")


def normalize_title(value: str) -> str:
    value = clean_book_title(value)
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("đ", "d").replace("Đ", "D").lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def resolve_epub_path(item: dict, json_dir: Path) -> Path | None:
    filename = item.get("filename")
    if filename:
        local_path = json_dir / filename
        if local_path.exists():
            return local_path

    raw_file = item.get("file")
    if raw_file:
        file_path = Path(raw_file)
        if file_path.exists():
            return file_path

    return None


def metadata_lines(item: dict) -> list[str]:
    title = clean_book_title(item.get("ten_truyen", ""))
    author = re.sub(r"\s+", " ", item.get("tac_gia") or "Chưa rõ").strip()
    tags = item.get("tags") or []
    genres = ", ".join(str(tag).strip() for tag in tags if str(tag).strip())
    return [
        f"title={title}",
        f"author={author}",
        f"status={item.get('status') or 'Hoàn thành'}",
        f"source_type={item.get('source_type') or 'Dịch'}",
        f"ranking={item.get('ranking')}",
        f"genres={genres}",
        f"description={item.get('description') or ''}",
    ]


def write_book_info(book_dir: Path, item: dict):
    book_info_path = book_dir / "book_info.txt"
    book_info_path.write_text("\n".join(metadata_lines(item)) + "\n", encoding="utf-8")


def expected_book_dir(item: dict, output_dir: Path) -> Path:
    title = clean_book_title(item.get("ten_truyen", ""))
    return output_dir / epub_to_md.translated_folder_name(title)


def read_book_info_title(book_dir: Path) -> str:
    book_info_path = book_dir / "book_info.txt"
    if not book_info_path.exists():
        return ""

    for line in book_info_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.lower().startswith("title="):
            return line.split("=", 1)[1].strip()
    return ""


def find_converted_book_dir(item: dict, output_dir: Path) -> Path:
    expected = expected_book_dir(item, output_dir)
    if expected.exists():
        return expected

    wanted = normalize_title(item.get("ten_truyen", ""))
    for book_dir in output_dir.glob("*_Translated"):
        if normalize_title(read_book_info_title(book_dir)) == wanted:
            return book_dir

    return expected


def select_items(data: list[dict], count: int, offset: int = 0) -> list[dict]:
    candidates = [
        item for item in data
        if not item.get("uploaded") and not item.get("duplicate")
    ]
    candidates.sort(key=lambda item: (
        item.get("ranking") if item.get("ranking") is not None else 10**9,
        item.get("ten_truyen") or "",
    ))

    eligible = []
    seen_titles = set()
    for item in candidates:
        key = normalize_title(item.get("ten_truyen", ""))
        if not key or key in seen_titles:
            continue
        seen_titles.add(key)
        eligible.append(item)

    return eligible[offset:offset + count]


def get_database_chapter_count(title: str) -> int | None:
    res = upload_translated.supabase.table("books").select("id,chapter_count").eq("title", title).execute()
    if not res.data:
        return None
    return int(res.data[0].get("chapter_count") or 0)


def convert_item(item: dict, json_dir: Path, output_dir: Path) -> Path | None:
    title = clean_book_title(item.get("ten_truyen", ""))
    epub_path = resolve_epub_path(item, json_dir)
    if not epub_path:
        print(f"❌ Không tìm thấy EPUB: {item.get('filename')}")
        return None

    book_dir = epub_to_md.convert_to_chapters(str(epub_path), str(output_dir))
    if not book_dir:
        print(f"❌ Convert thất bại: {title}")
        return None

    book_dir_path = Path(book_dir)
    write_book_info(book_dir_path, item)
    return book_dir_path


def upload_item(item: dict, book_dir_path: Path, json_path: Path, data: list[dict]) -> bool:
    title = clean_book_title(item.get("ten_truyen", ""))
    if not book_dir_path.exists():
        print(f"❌ Chưa có folder convert: {book_dir_path}")
        return False

    upload_translated.upload_chapters(str(book_dir_path))

    local_chapter_count = len(list(book_dir_path.glob("*.md")))
    database_chapter_count = get_database_chapter_count(title)
    if database_chapter_count is not None and database_chapter_count >= local_chapter_count:
        item["uploaded"] = True
        item["duplicate"] = True
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"✅ Đã đánh dấu uploaded=true trong JSON: {title}")
        return True

    print(
        "⚠️ Chưa xác nhận đủ chương trên DB, chưa đánh dấu uploaded=true: "
        f"{title} ({database_chapter_count or 0}/{local_chapter_count})"
    )
    return False


def main():
    parser = argparse.ArgumentParser(description="Convert/upload prioritized books from all_tien_hiep.json.")
    parser.add_argument("--json", default=str(DEFAULT_JSON_PATH), help="Path to all_tien_hiep.json")
    parser.add_argument("--count", type=int, default=20, help="Number of eligible books to process")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N eligible books before selecting.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output chapters directory")
    parser.add_argument("--dry-run", action="store_true", help="Print selected books without converting/uploading")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--convert-only", action="store_true", help="Only convert EPUB to Markdown folders.")
    mode.add_argument("--upload-only", action="store_true", help="Only upload existing converted folders.")
    args = parser.parse_args()

    json_path = Path(args.json).resolve()
    output_dir = Path(args.output_dir).resolve()
    if not json_path.exists():
        print(f"❌ Không tìm thấy JSON: {json_path}")
        sys.exit(1)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print("❌ JSON root phải là list.")
        sys.exit(1)

    if args.offset < 0:
        print("❌ --offset phải >= 0.")
        sys.exit(1)

    selected = select_items(data, args.count, args.offset)
    if not selected:
        print("⚠️ Không có truyện eligible để xử lý.")
        return

    print(f"📚 Sẽ xử lý {len(selected)} truyện:")
    for index, item in enumerate(selected, 1):
        print(f"  {index:02d}. ranking={item.get('ranking')} | {clean_book_title(item.get('ten_truyen', ''))}")

    if args.dry_run:
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    processed_titles = []
    for index, item in enumerate(selected, 1):
        title = clean_book_title(item.get("ten_truyen", ""))
        print(f"\n{'=' * 72}")
        print(f"[{index}/{len(selected)}] {title}")

        if args.upload_only:
            book_dir_path = find_converted_book_dir(item, output_dir)
        else:
            book_dir_path = convert_item(item, json_path.parent, output_dir)
            if not book_dir_path:
                continue

        if args.convert_only:
            md_count = len(list(book_dir_path.glob("*.md")))
            print(f"✅ Convert-only xong: {book_dir_path} ({md_count} file .md)")
            processed_titles.append(title)
            continue

        if upload_item(item, book_dir_path, json_path, data):
            processed_titles.append(title)

    action = "Converted" if args.convert_only else "Uploaded confirmed"
    print(f"\n🏁 Hoàn tất batch. {action}: {len(processed_titles)}/{len(selected)}")
    for title in processed_titles:
        print(f"  - {title}")


if __name__ == "__main__":
    main()
