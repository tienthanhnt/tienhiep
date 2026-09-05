#!/usr/bin/env python3
"""
Repair cover_url for Cloudflare D1 books by uploading local covers to R2.

Default mode is dry-run and only targets books whose cover is missing/default.
Use --yes to apply changes, or --all --yes to re-upload every matched cover.
"""

import argparse
from pathlib import Path

from dotenv import load_dotenv

from cloudflare_store import d1_rows
from upload_new_d1_r2 import (
    upload_cover_image_r2,
    update_book_cover,
)
from upload_translated import DEFAULT_COVER, read_book_info


load_dotenv()


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CHAPTERS_DIR = SCRIPT_DIR / "chapters"
DEFAULT_COVER_MARKER = "images.unsplash.com/photo-1541963463532-d68292c34b19"


def normalize_title(title: str) -> str:
    return " ".join((title or "").strip().casefold().split())


def is_default_or_missing_cover(cover_url: str | None) -> bool:
    if not cover_url:
        return True
    return cover_url == DEFAULT_COVER or DEFAULT_COVER_MARKER in cover_url


def collect_local_books(chapters_dir: Path) -> tuple[dict[str, tuple[Path, dict]], list[str]]:
    books: dict[str, tuple[Path, dict]] = {}
    warnings: list[str] = []

    if not chapters_dir.is_dir():
        raise SystemExit(f"❌ Không tìm thấy thư mục chapters: {chapters_dir}")

    for book_dir in sorted(path for path in chapters_dir.iterdir() if path.is_dir()):
        info_path = book_dir / "book_info.txt"
        if not info_path.exists():
            continue

        book_info = read_book_info(str(book_dir))
        title = (book_info.get("title") or "").strip()
        if not title or title == "Chưa đặt tên":
            warnings.append(f"⚠️  Bỏ qua {book_dir.name}: thiếu title trong book_info.txt")
            continue

        key = normalize_title(title)
        if key in books:
            previous_dir = books[key][0]
            warnings.append(
                f"⚠️  Trùng title '{title}': dùng {previous_dir.name}, bỏ qua {book_dir.name}"
            )
            continue

        books[key] = (book_dir, book_info)

    return books, warnings


def fetch_d1_books() -> list[dict]:
    return d1_rows(
        """
        SELECT id, public_id, title, author, cover_url
        FROM books
        ORDER BY id ASC
        """
    )


def cover_status(cover_url: str | None) -> str:
    if is_default_or_missing_cover(cover_url):
        return "DEFAULT"
    if "r2.dev/" in cover_url or ".r2.cloudflarestorage.com/" in cover_url:
        return "R2"
    return "OTHER"


def build_candidates(
    d1_books: list[dict],
    local_books: dict[str, tuple[Path, dict]],
    force_all: bool,
) -> tuple[list[tuple[dict, Path, dict]], list[dict], list[dict]]:
    candidates: list[tuple[dict, Path, dict]] = []
    missing_local: list[dict] = []
    skipped_ok: list[dict] = []

    for book in d1_books:
        cover_url = book.get("cover_url")
        if not force_all and not is_default_or_missing_cover(cover_url):
            skipped_ok.append(book)
            continue

        local = local_books.get(normalize_title(str(book.get("title") or "")))
        if not local:
            missing_local.append(book)
            continue

        book_dir, book_info = local
        candidates.append((book, book_dir, book_info))

    return candidates, missing_local, skipped_ok


def print_summary(
    candidates: list[tuple[dict, Path, dict]],
    missing_local: list[dict],
    skipped_ok: list[dict],
    limit: int | None,
    dry_run: bool,
) -> None:
    visible_candidates = candidates[:limit] if limit else candidates

    print("\n📊 Kết quả scan cover D1/R2:")
    print(f"Truyện cần cập nhật cover : {len(candidates):,}")
    if limit:
        print(f"Giới hạn lần chạy này     : {len(visible_candidates):,}/{len(candidates):,}")
    print(f"Truyện đã có cover ổn     : {len(skipped_ok):,}")
    print(f"Truyện thiếu folder local : {len(missing_local):,}")

    if visible_candidates:
        print("\nCác truyện sẽ được xử lý:")
        for book, book_dir, _book_info in visible_candidates[:30]:
            public_id = book.get("public_id") or f"id-{book.get('id')}"
            print(
                f"- {public_id} | {book.get('title')} | "
                f"{cover_status(book.get('cover_url'))} | {book_dir.name}"
            )
        if len(visible_candidates) > 30:
            print(f"... và {len(visible_candidates) - 30:,} truyện nữa")

    if missing_local:
        print("\nMột số truyện trên D1 nhưng không tìm thấy folder local:")
        for book in missing_local[:20]:
            public_id = book.get("public_id") or f"id-{book.get('id')}"
            print(f"- {public_id} | {book.get('title')} | {cover_status(book.get('cover_url'))}")
        if len(missing_local) > 20:
            print(f"... và {len(missing_local) - 20:,} truyện nữa")

    if dry_run:
        print("\n✅ Dry-run xong. Chưa upload/cập nhật gì.")
        print("Muốn repair cover lỗi/default: python repair_d1_r2_covers.py --yes")
        print("Muốn ép upload lại tất cả cover: python repair_d1_r2_covers.py --all --yes")


def repair_covers(candidates: list[tuple[dict, Path, dict]], limit: int | None) -> None:
    selected = candidates[:limit] if limit else candidates
    repaired = 0
    failed = 0

    for index, (book, book_dir, book_info) in enumerate(selected, start=1):
        book_id = int(book["id"])
        title = str(book.get("title") or book_info.get("title") or "")
        author = str(book.get("author") or book_info.get("author") or "Chưa rõ")
        public_id = book.get("public_id") or f"id-{book_id}"

        print("\n" + "=" * 70)
        print(f"🖼️  [{index}/{len(selected)}] Repair cover: {public_id} | {title}")
        cover_url = upload_cover_image_r2(str(book_dir), title, author)
        if is_default_or_missing_cover(cover_url):
            failed += 1
            print("❌ Không cập nhật vì upload/tạo cover thất bại.")
            continue

        update_book_cover(book_id, cover_url)
        repaired += 1
        print(f"✅ Đã cập nhật cover_url: {cover_url}")

    print("\n🎉 Hoàn tất repair cover D1/R2.")
    print(f"Đã cập nhật : {repaired:,}")
    print(f"Lỗi/bỏ qua  : {failed:,}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair hàng loạt cover D1/R2 từ folder local chapters.")
    parser.add_argument(
        "--chapters-dir",
        default=str(DEFAULT_CHAPTERS_DIR),
        help="Thư mục chứa các folder truyện. Mặc định: importer/chapters",
    )
    parser.add_argument("--limit", type=int, default=None, help="Chỉ xử lý N truyện đầu.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Upload lại cover cho mọi truyện D1 tìm thấy folder local, kể cả cover đang ổn.",
    )
    parser.add_argument("--yes", action="store_true", help="Thực sự upload R2 và cập nhật D1.")
    args = parser.parse_args()

    chapters_dir = Path(args.chapters_dir).expanduser().resolve()
    local_books, warnings = collect_local_books(chapters_dir)
    for warning in warnings[:30]:
        print(warning)
    if len(warnings) > 30:
        print(f"⚠️  ... còn {len(warnings) - 30:,} cảnh báo folder local nữa")

    print(f"🔎 Đã đọc {len(local_books):,} folder local có book_info.txt")
    print("🔎 Đang đọc danh sách books trên D1...")
    d1_books = fetch_d1_books()
    print(f"🔎 Đã đọc {len(d1_books):,} truyện trên D1")

    candidates, missing_local, skipped_ok = build_candidates(d1_books, local_books, args.all)
    print_summary(candidates, missing_local, skipped_ok, args.limit, dry_run=not args.yes)

    if not args.yes:
        return 0

    if not candidates:
        print("✅ Không có cover nào cần repair.")
        return 0

    repair_covers(candidates, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
