"""
analyze_chapter_storage.py — Thống kê chính xác bucket chapter-content.

Mặc định chỉ đọc dữ liệu, không xóa gì:
  python analyze_chapter_storage.py

Xem thêm một số path orphan mẫu:
  python analyze_chapter_storage.py --sample 50

Xóa thử 1000 orphan đầu tiên:
  python analyze_chapter_storage.py --delete --yes --limit 1000

Xóa toàn bộ orphan:
  python analyze_chapter_storage.py --delete --yes
"""

import argparse
import os
import sys
from collections import defaultdict

from dotenv import load_dotenv
from supabase import create_client, Client


load_dotenv()

SUPABASE_URL: str | None = os.environ.get("SUPABASE_URL")
SUPABASE_KEY: str | None = os.environ.get("SUPABASE_KEY")
CONTENT_STORAGE_BUCKET = "chapter-content"
CHAPTERS_PAGE_SIZE = 1000
STORAGE_PAGE_SIZE = 1000
DELETE_BATCH_SIZE = 100

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Lỗi: Bạn cần điền SUPABASE_URL và SUPABASE_KEY trong file .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


def book_id_from_path(path: str) -> str:
    return path.split("/", 1)[0] if "/" in path else "(root)"


def fetch_chapter_refs() -> dict[str, dict]:
    refs: dict[str, dict] = {}
    offset = 0

    while True:
        res = (
            supabase.table("chapters")
            .select("id, book_id, chapter_number, title, content_path")
            .order("id")
            .range(offset, offset + CHAPTERS_PAGE_SIZE - 1)
            .execute()
        )
        rows = res.data or []
        for row in rows:
            content_path = row.get("content_path")
            if content_path:
                refs[content_path] = row

        print(f"   Đã đọc {offset + len(rows)} chapter rows...", end="\r")
        if len(rows) < CHAPTERS_PAGE_SIZE:
            print()
            break
        offset += CHAPTERS_PAGE_SIZE

    return refs


def fetch_book_titles(book_ids: set[int]) -> dict[int, str]:
    titles: dict[int, str] = {}
    ids = sorted(book_ids)
    for start in range(0, len(ids), 100):
        batch = ids[start:start + 100]
        res = (
            supabase.table("books")
            .select("id, title")
            .in_("id", batch)
            .execute()
        )
        for row in res.data or []:
            titles[row["id"]] = row.get("title") or ""

    return titles


def fetch_referenced_paths(paths: list[str]) -> set[str]:
    if not paths:
        return set()

    res = (
        supabase.table("chapters")
        .select("content_path")
        .in_("content_path", paths)
        .execute()
    )
    return {row["content_path"] for row in (res.data or []) if row.get("content_path")}


def list_storage_objects(prefix: str = "") -> dict[str, int]:
    objects: dict[str, int] = {}
    offset = 0

    while True:
        rows = supabase.storage.from_(CONTENT_STORAGE_BUCKET).list(
            prefix,
            {
                "limit": STORAGE_PAGE_SIZE,
                "offset": offset,
                "sortBy": {"column": "name", "order": "asc"},
            },
        )

        if not rows:
            break

        for item in rows:
            name = item.get("name")
            if not name:
                continue

            object_name = f"{prefix.rstrip('/')}/{name}".strip("/")
            metadata = item.get("metadata")

            if metadata is None and item.get("id") is None:
                objects.update(list_storage_objects(object_name))
                continue

            try:
                size = int((metadata or {}).get("size") or 0)
            except (TypeError, ValueError):
                size = 0
            objects[object_name] = size

        if len(rows) < STORAGE_PAGE_SIZE:
            break
        offset += STORAGE_PAGE_SIZE

    return objects


def summarize_by_book(paths: list[str], sizes: dict[str, int], limit: int) -> list[tuple[str, int, int]]:
    summary: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for path in paths:
        book_id = book_id_from_path(path)
        summary[book_id][0] += 1
        summary[book_id][1] += sizes.get(path, 0)

    rows = [(book_id, values[0], values[1]) for book_id, values in summary.items()]
    return sorted(rows, key=lambda row: row[2], reverse=True)[:limit]


def summarize_missing_by_book(
    paths: list[str],
    chapter_refs: dict[str, dict],
    book_titles: dict[int, str],
    limit: int,
) -> list[tuple[int, str, int, int | None, int | None]]:
    summary: dict[int, dict] = {}

    for path in paths:
        ref = chapter_refs.get(path) or {}
        book_id = ref.get("book_id")
        if book_id is None:
            continue

        chapter_number = ref.get("chapter_number")
        item = summary.setdefault(
            book_id,
            {
                "count": 0,
                "min_chapter": chapter_number,
                "max_chapter": chapter_number,
            },
        )
        item["count"] += 1

        if isinstance(chapter_number, int):
            if item["min_chapter"] is None or chapter_number < item["min_chapter"]:
                item["min_chapter"] = chapter_number
            if item["max_chapter"] is None or chapter_number > item["max_chapter"]:
                item["max_chapter"] = chapter_number

    rows = [
        (book_id, book_titles.get(book_id, ""), item["count"], item["min_chapter"], item["max_chapter"])
        for book_id, item in summary.items()
    ]
    return sorted(rows, key=lambda row: row[2], reverse=True)[:limit]


def print_book_summary(title: str, rows: list[tuple[str, int, int]]):
    if not rows:
        return

    print(f"\n{title}")
    print(f"{'book_id':<12} {'files':>10} {'size':>14}")
    print("-" * 40)
    for book_id, count, size in rows:
        print(f"{book_id:<12} {count:>10,} {format_bytes(size):>14}")


def print_missing_summary(title: str, rows: list[tuple[int, str, int, int | None, int | None]]):
    if not rows:
        return

    print(f"\n{title}")
    print(f"{'book_id':<8} {'missing':>8} {'chapters':>18}  title")
    print("-" * 80)
    for book_id, book_title, count, min_chapter, max_chapter in rows:
        chapter_range = "-"
        if min_chapter is not None and max_chapter is not None:
            chapter_range = str(min_chapter) if min_chapter == max_chapter else f"{min_chapter}-{max_chapter}"
        print(f"{book_id:<8} {count:>8,} {chapter_range:>18}  {book_title}")


def remove_storage_objects(paths: list[str]) -> int:
    removed = 0
    skipped = 0
    for start in range(0, len(paths), DELETE_BATCH_SIZE):
        batch = paths[start:start + DELETE_BATCH_SIZE]
        referenced = fetch_referenced_paths(batch)
        safe_batch = [path for path in batch if path not in referenced]
        skipped += len(batch) - len(safe_batch)

        if safe_batch:
            supabase.storage.from_(CONTENT_STORAGE_BUCKET).remove(safe_batch)
            removed += len(safe_batch)

        print(
            f"🗑️  Đã xóa {removed:,}/{len(paths):,} file orphan..."
            f" bỏ qua {skipped:,} file vừa phát hiện DB còn dùng",
        )
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run thống kê file chapter-content đang dùng và orphan."
    )
    parser.add_argument("--sample", type=int, default=20, help="Số orphan path mẫu cần in. Mặc định: 20")
    parser.add_argument("--top", type=int, default=20, help="Số book_id lớn nhất cần in. Mặc định: 20")
    parser.add_argument("--limit", type=int, default=None, help="Giới hạn số orphan để report/xóa.")
    parser.add_argument("--delete", action="store_true", help="Xóa thật các orphan file trong chapter-content.")
    parser.add_argument("--yes", action="store_true", help="Xác nhận xóa thật, bắt buộc đi kèm --delete.")
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        print("❌ --limit phải lớn hơn 0.")
        sys.exit(1)

    print("🔎 Đang đọc chapters.content_path trong DB...")
    chapter_refs = fetch_chapter_refs()
    used_paths = set(chapter_refs)

    print(f"🔎 Đang scan bucket Storage '{CONTENT_STORAGE_BUCKET}'...")
    stored_sizes = list_storage_objects()
    stored_paths = set(stored_sizes)

    used_in_storage = sorted(stored_paths & used_paths)
    all_orphan_paths = sorted(stored_paths - used_paths)
    orphan_paths = all_orphan_paths[:args.limit] if args.limit is not None else all_orphan_paths
    missing_storage_paths = sorted(used_paths - stored_paths)
    missing_book_ids = {
        chapter_refs[path]["book_id"]
        for path in missing_storage_paths
        if chapter_refs.get(path, {}).get("book_id") is not None
    }
    book_titles = fetch_book_titles(missing_book_ids) if missing_book_ids else {}

    stored_size = sum(stored_sizes.values())
    used_size = sum(stored_sizes[path] for path in used_in_storage)
    all_orphan_size = sum(stored_sizes[path] for path in all_orphan_paths)
    orphan_size = sum(stored_sizes[path] for path in orphan_paths)

    print("\n📊 Kết quả dry-run:")
    print(f"   DB content_path đang dùng       : {len(used_paths):,}")
    print(f"   File trong bucket chapter-content: {len(stored_paths):,}")
    print(f"   File DB dùng và còn trên Storage : {len(used_in_storage):,}")
    print(f"   File orphan có thể cân nhắc xóa  : {len(all_orphan_paths):,}")
    if args.limit is not None:
        print(f"   File orphan trong limit lần này   : {len(orphan_paths):,}")
    print(f"   File DB trỏ tới nhưng thiếu file : {len(missing_storage_paths):,}")
    print("")
    print(f"   Tổng dung lượng bucket           : {format_bytes(stored_size)}")
    print(f"   Dung lượng file đang được DB dùng: {format_bytes(used_size)}")
    print(f"   Dung lượng orphan ước tính       : {format_bytes(all_orphan_size)}")
    if args.limit is not None:
        print(f"   Dung lượng orphan trong limit     : {format_bytes(orphan_size)}")

    print_book_summary(
        f"Top {args.top} book_id chiếm dung lượng nhiều nhất:",
        summarize_by_book(sorted(stored_paths), stored_sizes, args.top),
    )
    print_book_summary(
        f"Top {args.top} book_id có orphan nhiều nhất:",
        summarize_by_book(all_orphan_paths, stored_sizes, args.top),
    )
    print_missing_summary(
        f"Top {args.top} truyện đang lỗi thiếu file Storage:",
        summarize_missing_by_book(missing_storage_paths, chapter_refs, book_titles, args.top),
    )

    if orphan_paths and args.sample > 0:
        print(f"\nMột số orphan path mẫu ({min(args.sample, len(orphan_paths))}/{len(orphan_paths)}):")
        for path in orphan_paths[:args.sample]:
            print(f"   - {path} ({format_bytes(stored_sizes.get(path, 0))})")

    if missing_storage_paths and args.sample > 0:
        print(f"\nMột số path DB đang trỏ tới nhưng thiếu trên Storage ({min(args.sample, len(missing_storage_paths))}/{len(missing_storage_paths)}):")
        for path in missing_storage_paths[:args.sample]:
            ref = chapter_refs.get(path) or {}
            book_id = ref.get("book_id")
            book_title = book_titles.get(book_id, "") if book_id is not None else ""
            chapter_number = ref.get("chapter_number")
            title = ref.get("title") or ""
            print(f"   - book_id={book_id} | {book_title} | chương {chapter_number}: {title} | {path}")

    if not args.delete:
        print("\n✅ Dry-run xong. Script này chưa xóa file nào.")
        print("   Muốn xóa thử 1000 orphan, chạy: python analyze_chapter_storage.py --delete --yes --limit 1000")
        print("   Muốn xóa toàn bộ orphan, chạy: python analyze_chapter_storage.py --delete --yes")
        return

    if not args.yes:
        print("\n❌ Để xóa thật cần thêm --yes.")
        return

    if not orphan_paths:
        print("\n✅ Không có orphan file để xóa.")
        return

    print("\n🚨 Bắt đầu xóa orphan file khỏi Storage...")
    removed = remove_storage_objects(orphan_paths)
    print(f"✅ Hoàn tất. Đã xóa {removed:,} orphan file, ước tính giải phóng {format_bytes(orphan_size)}.")


if __name__ == "__main__":
    main()
