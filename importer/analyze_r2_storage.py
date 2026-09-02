"""
analyze_r2_storage.py — Thống kê chính xác bucket Cloudflare R2 cho nguồn D1/R2.

Mặc định chỉ đọc dữ liệu, không xóa gì:
  python analyze_r2_storage.py

Chỉ scan chapter hoặc cover:
  python analyze_r2_storage.py --prefix chapters/
  python analyze_r2_storage.py --prefix covers/

Xóa thử 1000 orphan đầu tiên:
  python analyze_r2_storage.py --delete --yes --limit 1000

Xóa toàn bộ orphan:
  python analyze_r2_storage.py --delete --yes
"""

import argparse
import sys
from collections import defaultdict

from dotenv import load_dotenv

from cloudflare_store import create_r2_client, d1_rows


load_dotenv()

CHAPTERS_PAGE_SIZE = 1000
BOOKS_PAGE_SIZE = 1000
R2_DELETE_BATCH_SIZE = 1000


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


def key_from_public_url(url: str, public_base_url: str) -> str | None:
    if not url:
        return None

    base = public_base_url.rstrip("/") + "/"
    if not url.startswith(base):
        return None

    return url[len(base):].lstrip("/") or None


def group_key(path: str) -> str:
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "chapters":
        return parts[1]
    if len(parts) >= 2 and parts[0] == "covers":
        return "covers"
    return parts[0] if parts else "(root)"


def fetch_d1_books() -> tuple[dict[int, dict], dict[str, dict], set[str]]:
    books_by_id: dict[int, dict] = {}
    books_by_public_id: dict[str, dict] = {}
    cover_paths: set[str] = set()
    env_public_base = None

    try:
        from cloudflare_store import require_env, R2_REQUIRED_ENV

        env_public_base = require_env(R2_REQUIRED_ENV)["R2_PUBLIC_BASE_URL"]
    except SystemExit:
        raise
    except Exception:
        env_public_base = None

    offset = 0
    while True:
        rows = d1_rows(
            """
            SELECT id, public_id, title, cover_url, chapter_count
            FROM books
            ORDER BY id ASC
            LIMIT ? OFFSET ?
            """,
            [BOOKS_PAGE_SIZE, offset],
        )
        for row in rows:
            book_id = int(row["id"])
            public_id = row.get("public_id") or f"new-{book_id}"
            books_by_id[book_id] = row
            books_by_public_id[public_id] = row

            if env_public_base:
                cover_key = key_from_public_url(row.get("cover_url") or "", env_public_base)
                if cover_key:
                    cover_paths.add(cover_key)

        if len(rows) < BOOKS_PAGE_SIZE:
            break
        offset += BOOKS_PAGE_SIZE

    return books_by_id, books_by_public_id, cover_paths


def fetch_d1_chapter_refs() -> dict[str, dict]:
    refs: dict[str, dict] = {}
    offset = 0

    while True:
        rows = d1_rows(
            """
            SELECT id, book_id, chapter_number, title, content_path
            FROM chapters
            WHERE content_path != ''
            ORDER BY id ASC
            LIMIT ? OFFSET ?
            """,
            [CHAPTERS_PAGE_SIZE, offset],
        )
        for row in rows:
            content_path = row.get("content_path")
            if content_path:
                refs[content_path] = row

        print(f"   Đã đọc {offset + len(rows)} D1 chapter rows...", end="\r")
        if len(rows) < CHAPTERS_PAGE_SIZE:
            print()
            break
        offset += CHAPTERS_PAGE_SIZE

    return refs


def list_r2_objects(prefix: str = "") -> dict[str, int]:
    client, env = create_r2_client()
    paginator = client.get_paginator("list_objects_v2")
    objects: dict[str, int] = {}

    page_iterator = paginator.paginate(Bucket=env["R2_BUCKET"], Prefix=prefix)
    scanned = 0
    for page in page_iterator:
        for item in page.get("Contents") or []:
            key = item.get("Key")
            if not key:
                continue
            size = int(item.get("Size") or 0)
            if key.endswith("/") and size == 0:
                continue
            objects[key] = size
            scanned += 1
        print(f"   Đã scan {scanned} R2 objects...", end="\r")

    print()
    return objects


def summarize_by_group(paths: list[str], sizes: dict[str, int], limit: int) -> list[tuple[str, int, int]]:
    summary: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for path in paths:
        key = group_key(path)
        summary[key][0] += 1
        summary[key][1] += sizes.get(path, 0)

    rows = [(key, values[0], values[1]) for key, values in summary.items()]
    return sorted(rows, key=lambda row: row[2], reverse=True)[:limit]


def summarize_missing_by_book(
    paths: list[str],
    chapter_refs: dict[str, dict],
    books_by_id: dict[int, dict],
    limit: int,
) -> list[tuple[str, str, int, int | None, int | None]]:
    summary: dict[str, dict] = {}

    for path in paths:
        ref = chapter_refs.get(path) or {}
        book_id = ref.get("book_id")
        if book_id is None:
            continue

        book = books_by_id.get(int(book_id), {})
        public_id = book.get("public_id") or f"new-{book_id}"
        chapter_number = ref.get("chapter_number")
        item = summary.setdefault(
            public_id,
            {
                "title": book.get("title") or "",
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
        (public_id, item["title"], item["count"], item["min_chapter"], item["max_chapter"])
        for public_id, item in summary.items()
    ]
    return sorted(rows, key=lambda row: row[2], reverse=True)[:limit]


def print_group_summary(title: str, rows: list[tuple[str, int, int]]):
    if not rows:
        return

    print(f"\n{title}")
    print(f"{'group':<18} {'files':>10} {'size':>14}")
    print("-" * 46)
    for group, count, size in rows:
        print(f"{group:<18} {count:>10,} {format_bytes(size):>14}")


def print_missing_summary(title: str, rows: list[tuple[str, str, int, int | None, int | None]]):
    if not rows:
        return

    print(f"\n{title}")
    print(f"{'public_id':<12} {'missing':>8} {'chapters':>18}  title")
    print("-" * 90)
    for public_id, book_title, count, min_chapter, max_chapter in rows:
        chapter_range = "-"
        if min_chapter is not None and max_chapter is not None:
            chapter_range = str(min_chapter) if min_chapter == max_chapter else f"{min_chapter}-{max_chapter}"
        print(f"{public_id:<12} {count:>8,} {chapter_range:>18}  {book_title}")


def delete_r2_objects(paths: list[str]) -> int:
    client, env = create_r2_client()
    removed = 0

    for start in range(0, len(paths), R2_DELETE_BATCH_SIZE):
        batch = paths[start:start + R2_DELETE_BATCH_SIZE]
        client.delete_objects(
            Bucket=env["R2_BUCKET"],
            Delete={"Objects": [{"Key": path} for path in batch], "Quiet": True},
        )
        removed += len(batch)
        print(f"🗑️  Đã xóa {removed:,}/{len(paths):,} orphan object khỏi R2...")

    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run thống kê file R2 đang dùng và orphan theo D1.")
    parser.add_argument("--prefix", default="", help="Chỉ scan object R2 dưới prefix này, ví dụ chapters/ hoặc covers/.")
    parser.add_argument("--sample", type=int, default=20, help="Số orphan/missing path mẫu cần in. Mặc định: 20")
    parser.add_argument("--top", type=int, default=20, help="Số group lớn nhất cần in. Mặc định: 20")
    parser.add_argument("--limit", type=int, default=None, help="Giới hạn số orphan để report/xóa.")
    parser.add_argument("--delete", action="store_true", help="Xóa thật các orphan object trong R2.")
    parser.add_argument("--yes", action="store_true", help="Xác nhận xóa thật, bắt buộc đi kèm --delete.")
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        print("❌ --limit phải lớn hơn 0.")
        sys.exit(1)

    print("🔎 Đang đọc books/chapters trong D1...")
    books_by_id, _, cover_paths = fetch_d1_books()
    chapter_refs = fetch_d1_chapter_refs()
    used_paths_all = set(chapter_refs) | cover_paths
    used_paths = {path for path in used_paths_all if not args.prefix or path.startswith(args.prefix)}

    print(f"🔎 Đang scan bucket R2 prefix '{args.prefix or '(all)'}'...")
    stored_sizes = list_r2_objects(args.prefix)
    stored_paths = set(stored_sizes)

    used_in_storage = sorted(stored_paths & used_paths)
    all_orphan_paths = sorted(stored_paths - used_paths)
    orphan_paths = all_orphan_paths[:args.limit] if args.limit is not None else all_orphan_paths
    missing_r2_paths = sorted(used_paths - stored_paths)

    stored_size = sum(stored_sizes.values())
    used_size = sum(stored_sizes[path] for path in used_in_storage)
    all_orphan_size = sum(stored_sizes[path] for path in all_orphan_paths)
    orphan_size = sum(stored_sizes[path] for path in orphan_paths)

    print("\n📊 Kết quả dry-run:")
    print(f"   D1 content_path/cover đang dùng : {len(used_paths):,}")
    print(f"   File trong bucket R2            : {len(stored_paths):,}")
    print(f"   File D1 dùng và còn trên R2     : {len(used_in_storage):,}")
    print(f"   File orphan có thể cân nhắc xóa : {len(all_orphan_paths):,}")
    if args.limit is not None:
        print(f"   File orphan trong limit lần này  : {len(orphan_paths):,}")
    print(f"   File D1 trỏ tới nhưng thiếu R2   : {len(missing_r2_paths):,}")
    print("")
    print(f"   Tổng dung lượng R2 scan được     : {format_bytes(stored_size)}")
    print(f"   Dung lượng file đang được D1 dùng: {format_bytes(used_size)}")
    print(f"   Dung lượng orphan ước tính       : {format_bytes(all_orphan_size)}")
    if args.limit is not None:
        print(f"   Dung lượng orphan trong limit     : {format_bytes(orphan_size)}")

    print_group_summary(
        f"Top {args.top} group chiếm dung lượng nhiều nhất:",
        summarize_by_group(sorted(stored_paths), stored_sizes, args.top),
    )
    print_group_summary(
        f"Top {args.top} group có orphan nhiều nhất:",
        summarize_by_group(all_orphan_paths, stored_sizes, args.top),
    )
    print_missing_summary(
        f"Top {args.top} truyện đang lỗi thiếu file R2:",
        summarize_missing_by_book(missing_r2_paths, chapter_refs, books_by_id, args.top),
    )

    if orphan_paths and args.sample > 0:
        print(f"\nMột số orphan path mẫu ({min(args.sample, len(orphan_paths))}/{len(orphan_paths)}):")
        for path in orphan_paths[:args.sample]:
            print(f"   - {path} ({format_bytes(stored_sizes.get(path, 0))})")

    if missing_r2_paths and args.sample > 0:
        print(f"\nMột số path D1 đang trỏ tới nhưng thiếu trên R2 ({min(args.sample, len(missing_r2_paths))}/{len(missing_r2_paths)}):")
        for path in missing_r2_paths[:args.sample]:
            ref = chapter_refs.get(path) or {}
            book = books_by_id.get(int(ref.get("book_id") or 0), {}) if ref.get("book_id") is not None else {}
            if ref:
                public_id = book.get("public_id") or f"new-{ref.get('book_id')}"
                print(
                    f"   - {public_id} | "
                    f"{book.get('title') or ''} | chương {ref.get('chapter_number')}: "
                    f"{ref.get('title') or ''} | {path}"
                )
            else:
                print(f"   - cover/object: {path}")

    if not args.delete:
        print("\n✅ Dry-run xong. Script này chưa xóa file nào.")
        print("   Muốn xóa thử 1000 orphan, chạy: python analyze_r2_storage.py --delete --yes --limit 1000")
        print("   Muốn xóa toàn bộ orphan, chạy: python analyze_r2_storage.py --delete --yes")
        return

    if not args.yes:
        print("\n❌ Để xóa thật cần thêm --yes.")
        return

    if not orphan_paths:
        print("\n✅ Không có orphan object để xóa.")
        return

    print("\n🔎 Recheck D1 trước khi xóa để tránh xóa nhầm file vừa được upload...")
    _, _, latest_cover_paths = fetch_d1_books()
    latest_chapter_refs = fetch_d1_chapter_refs()
    latest_used_paths = set(latest_chapter_refs) | latest_cover_paths
    safe_orphan_paths = [path for path in orphan_paths if path not in latest_used_paths]
    skipped = len(orphan_paths) - len(safe_orphan_paths)
    if skipped:
        print(f"⚠️  Bỏ qua {skipped:,} object vì D1 vừa phát hiện còn dùng.")

    if not safe_orphan_paths:
        print("\n✅ Không còn orphan object an toàn để xóa.")
        return

    print("\n🚨 Bắt đầu xóa orphan object khỏi R2...")
    removed = delete_r2_objects(safe_orphan_paths)
    removed_size = sum(stored_sizes.get(path, 0) for path in safe_orphan_paths)
    print(f"✅ Hoàn tất. Đã xóa {removed:,} orphan object, ước tính giải phóng {format_bytes(removed_size)}.")


if __name__ == "__main__":
    main()
