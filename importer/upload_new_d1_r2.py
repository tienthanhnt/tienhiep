#!/usr/bin/env python3
import argparse
import gzip
import hashlib
import os
import re
import shutil
import time
from pathlib import Path

from dotenv import load_dotenv
import markdown

from cloudflare_store import d1_batch, d1_query, d1_rows, upload_r2_object
from supabase_lookup import find_supabase_book_by_title
from upload_translated import (
    CHAPTER_CACHE_CONTROL,
    COVER_CACHE_CONTROL,
    DEFAULT_COVER,
    UPLOAD_RETRY_COUNT,
    create_generated_cover,
    create_optimized_cover,
    find_cover_source,
    parse_optional_int,
    read_book_info,
    safe_ascii_storage_stem,
    safe_storage_name,
)


load_dotenv()


CHAPTER_INSERT_BATCH_SIZE = 200
NEW_SOURCE_PREFIX = "new"


def slugify_for_route(value: str) -> str:
    normalized = safe_ascii_storage_stem(value).replace("_", "-")
    return re.sub(r"-+", "-", normalized).strip("-")


def get_existing_book(title: str) -> dict | None:
    rows = d1_rows(
        """
        SELECT id, public_id, title, cover_url
        FROM books
        WHERE title = ?
        LIMIT 1
        """,
        [title],
    )
    return rows[0] if rows else None


def update_book_public_id(book_id: int) -> str:
    public_id = f"{NEW_SOURCE_PREFIX}-{book_id}"
    d1_query("UPDATE books SET public_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", [public_id, book_id])
    return public_id


def upload_cover_image_r2(translated_dir: str, book_title: str, author: str) -> str:
    upload_path = find_cover_source(translated_dir)
    optimized_cover = None
    generated_cover = None

    if upload_path:
        optimized_cover = create_optimized_cover(upload_path)
    else:
        print("ℹ️  Không tìm thấy theme.webp/theme.jpg/theme.jpeg/theme.png — tự tạo bìa chữ.")
        generated_cover = create_generated_cover(book_title, author)
        if generated_cover:
            local_cover_path = os.path.join(translated_dir, "theme.webp")
            shutil.copyfile(generated_cover[0], local_cover_path)
            print(f"🖼️  Đã tạo ảnh bìa local: {local_cover_path}")

    if optimized_cover:
        upload_path, content_type, extension = optimized_cover
    elif generated_cover:
        upload_path, content_type, extension = generated_cover
    elif not upload_path:
        print("⚠️  Không tạo được ảnh bìa tự động — dùng ảnh mặc định.")
        return DEFAULT_COVER
    else:
        suffix = Path(upload_path).suffix.lower()
        content_type = "image/png" if suffix == ".png" else "image/jpeg"
        extension = suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"

    try:
        image_bytes = Path(upload_path).read_bytes()
        safe_stem = safe_ascii_storage_stem(book_title)
        content_hash = hashlib.sha1(image_bytes).hexdigest()[:12]
        key = f"covers/{NEW_SOURCE_PREFIX}/{safe_stem}-{content_hash}{extension}"
        public_url = upload_r2_object(key, image_bytes, content_type, COVER_CACHE_CONTROL)
        print(f"🖼️  Đã upload ảnh bìa lên R2: {public_url}")
        return public_url
    except Exception as exc:
        print(f"⚠️  Lỗi upload ảnh bìa R2: {exc}")
        return DEFAULT_COVER
    finally:
        if optimized_cover or generated_cover:
            try:
                os.unlink(upload_path)
            except OSError:
                pass


def get_or_create_book(book_info: dict, cover_url: str) -> tuple[int, str]:
    title = book_info["title"]
    author = book_info["author"]
    ranking = parse_optional_int(book_info["ranking"], "ranking") or 0
    existing = get_existing_book(title)

    if existing:
        book_id = int(existing["id"])
        public_id = existing.get("public_id") or update_book_public_id(book_id)
        update_params = [
            author,
            book_info["status"],
            book_info["description"],
            book_info["genres"],
            book_info["source_type"],
            ranking,
            cover_url or existing.get("cover_url") or DEFAULT_COVER,
            book_id,
        ]
        d1_query(
            """
            UPDATE books
            SET author = ?, status = ?, description = ?, genres = ?, source_type = ?,
                ranking = ?, cover_url = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            update_params,
        )
        print(f"🔍 Đã tìm thấy/cập nhật truyện nguồn mới '{title}' (ID: {public_id})")
        return book_id, public_id

    d1_query(
        """
        INSERT INTO books (
          title, author, status, description, genres, source_type,
          ranking, rating, chapter_count, cover_url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 8.0, 0, ?)
        """,
        [
            title,
            author,
            book_info["status"],
            book_info["description"],
            book_info["genres"],
            book_info["source_type"],
            ranking,
            cover_url,
        ],
    )
    rows = d1_rows("SELECT id FROM books WHERE title = ? LIMIT 1", [title])
    book_id = int(rows[0]["id"])
    public_id = update_book_public_id(book_id)
    print(f"✅ Đã tạo truyện mới trên D1 với ID = {public_id}")
    return book_id, public_id


def get_existing_chapter_numbers(book_id: int) -> set[int]:
    rows = d1_rows("SELECT chapter_number FROM chapters WHERE book_id = ?", [book_id])
    return {int(row["chapter_number"]) for row in rows if row.get("chapter_number") is not None}


def upload_chapter_content_r2(
    public_id: str,
    chapter_number: int,
    chapter_title: str,
    html_content: str,
) -> tuple[str, str]:
    safe_title = safe_storage_name(chapter_title)
    content_path = f"chapters/{public_id}/{chapter_number:04d}_{safe_title}.html.gz"
    compressed_html = gzip.compress(html_content.encode("utf-8"), compresslevel=9)
    last_error = None

    for attempt in range(1, UPLOAD_RETRY_COUNT + 1):
        try:
            public_url = upload_r2_object(
                content_path,
                compressed_html,
                "application/gzip",
                CHAPTER_CACHE_CONTROL,
            )
            return content_path, public_url
        except Exception as exc:
            last_error = exc
            if attempt < UPLOAD_RETRY_COUNT:
                wait_seconds = attempt * 3
                print(f"⚠️  Upload R2 chương {chapter_number} lỗi lần {attempt}/{UPLOAD_RETRY_COUNT}: {exc}")
                print(f"   Chờ {wait_seconds}s rồi thử lại...")
                time.sleep(wait_seconds)

    raise RuntimeError(f"Lỗi upload R2 chương {chapter_number}: {last_error}")


def parse_chapter_file(file_path: Path, chapter_number: int) -> tuple[str, str]:
    md_content = file_path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", md_content, flags=re.MULTILINE)
    chapter_title = title_match.group(1).strip() if title_match else f"Chương {chapter_number}"
    return chapter_title, markdown.markdown(md_content)


def upload_chapters_new(
    translated_dir: str,
    limit: int | None = None,
    allow_supabase_duplicate: bool = False,
) -> None:
    print(f"📖 Đang upload nguồn mới D1 + R2 từ: {translated_dir}")

    book_dir = Path(translated_dir)
    if not book_dir.is_dir():
        print(f"❌ Không tìm thấy thư mục: {translated_dir}")
        return

    files = sorted(path for path in book_dir.iterdir() if path.name.endswith(".md"))
    if limit is not None:
        files = files[:limit]
        print(f"🧪 Chế độ upload thử: chỉ xử lý {len(files)} chương đầu.")

    if not files:
        print("⚠️ Không tìm thấy file .md nào trong thư mục dịch.")
        return

    book_info = read_book_info(str(book_dir))
    if not allow_supabase_duplicate:
        supabase_book = find_supabase_book_by_title(book_info["title"])
        if supabase_book:
            print("🛡️  Dừng upload để tránh trùng truyện với Supabase cũ.")
            print(
                f"   Truyện '{book_info['title']}' đã có trên Supabase "
                f"(ID {supabase_book.get('id')}, {supabase_book.get('chapter_count') or 0} chương)."
            )
            print("   Nếu cố ý muốn upload trùng lên D1/R2, thêm --allow-supabase-duplicate.")
            return

    existing_book = get_existing_book(book_info["title"])
    if existing_book:
        cover_url = existing_book.get("cover_url") or DEFAULT_COVER
        print("🖼️  Truyện đã có trên D1 — bỏ qua upload lại ảnh bìa.")
    else:
        cover_url = upload_cover_image_r2(str(book_dir), book_info["title"], book_info["author"])

    book_id, public_id = get_or_create_book(book_info, cover_url)
    existing_chapter_numbers = get_existing_chapter_numbers(book_id)
    if existing_chapter_numbers:
        print(f"🔎 Đã có {len(existing_chapter_numbers)} chương trên D1, tool sẽ bỏ qua các chương đó.")

    pending: list[tuple[object, ...]] = []
    inserted_count = 0
    failed_chapter = None

    def flush_batch():
        nonlocal pending, inserted_count
        if not pending:
            return
        batch = [
            {
                "sql": """
                    INSERT INTO chapters (
                      book_id, chapter_number, title, content_html, content_path, content_url
                    )
                    VALUES (?, ?, ?, '', ?, ?)
                    ON CONFLICT(book_id, chapter_number) DO NOTHING
                """,
                "params": list(row),
            }
            for row in pending
        ]
        d1_batch(batch)

        inserted_count += len(pending)
        print(f"  📦 Đã ghi {inserted_count} chương mới vào D1...")
        pending = []

    for file_path in files:
        match = re.match(r"^(\d+)_", file_path.name)
        if not match:
            continue

        chapter_number = int(match.group(1))
        if chapter_number in existing_chapter_numbers:
            print(f"[-] Bỏ qua Chương {chapter_number}: đã có trên D1.")
            continue

        chapter_title, html_content = parse_chapter_file(file_path, chapter_number)

        try:
            content_path, content_url = upload_chapter_content_r2(
                public_id,
                chapter_number,
                chapter_title,
                html_content,
            )
        except Exception as exc:
            failed_chapter = chapter_number
            print(f"❌ Dừng ở chương {chapter_number}: {exc}")
            break

        pending.append((book_id, chapter_number, chapter_title, content_path, content_url))
        existing_chapter_numbers.add(chapter_number)

        if len(pending) >= CHAPTER_INSERT_BATCH_SIZE:
            flush_batch()

    flush_batch()
    rows = d1_rows("SELECT COUNT(*) AS total FROM chapters WHERE book_id = ?", [book_id])
    total_chapters = int(rows[0]["total"] or 0)
    d1_query("UPDATE books SET chapter_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", [total_chapters, book_id])

    print(f"📌 Route truyện mới sẽ là: /books/{public_id}-{slugify_for_route(book_info['title'])}")
    print(f"📚 Tổng chương trên D1: {total_chapters}")
    if failed_chapter:
        print("⚠️  Có lỗi giữa chừng. Chạy lại cùng lệnh, tool sẽ bỏ qua các chương đã có và tiếp tục.")
    else:
        print("🎉 Upload nguồn mới D1 + R2 hoàn tất.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload truyện mới vào Cloudflare D1 + R2.")
    parser.add_argument("--translated-dir", required=True, help="Thư mục *_Translated chứa .md và book_info.txt.")
    parser.add_argument("--limit", type=int, default=None, help="Chỉ upload N chương đầu để test.")
    parser.add_argument(
        "--allow-supabase-duplicate",
        "--allow-supabase-duplicates",
        action="store_true",
        help="Cho phép upload lên D1/R2 dù truyện đã tồn tại trong Supabase cũ.",
    )
    args = parser.parse_args()
    upload_chapters_new(
        args.translated_dir,
        args.limit,
        allow_supabase_duplicate=args.allow_supabase_duplicate,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
