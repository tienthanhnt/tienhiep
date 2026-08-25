"""
cleanup_orphan_covers.py — Dọn ảnh bìa cũ không còn được books.cover_url dùng.

Mặc định chỉ dry-run để tránh xóa nhầm:
  python cleanup_orphan_covers.py

Xóa thật:
  python cleanup_orphan_covers.py --delete --yes
"""

import argparse
import os
import sys
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv
from supabase import create_client, Client


load_dotenv()

SUPABASE_URL: str | None = os.environ.get("SUPABASE_URL")
SUPABASE_KEY: str | None = os.environ.get("SUPABASE_KEY")
STORAGE_BUCKET = "covers"
BOOKS_PAGE_SIZE = 1000
STORAGE_PAGE_SIZE = 1000
DELETE_BATCH_SIZE = 100

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Lỗi: Bạn cần điền SUPABASE_URL và SUPABASE_KEY trong file .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def cover_object_name_from_url(cover_url: str) -> str | None:
    if not cover_url:
        return None

    parsed = urlparse(cover_url)
    marker = f"/storage/v1/object/public/{STORAGE_BUCKET}/"
    if marker not in parsed.path:
        return None

    object_name = parsed.path.split(marker, 1)[1].strip("/")
    return unquote(object_name) if object_name else None


def fetch_used_cover_names() -> set[str]:
    used: set[str] = set()
    offset = 0

    while True:
        res = (
            supabase.table("books")
            .select("cover_url")
            .range(offset, offset + BOOKS_PAGE_SIZE - 1)
            .execute()
        )
        rows = res.data or []
        for row in rows:
            object_name = cover_object_name_from_url(row.get("cover_url") or "")
            if object_name:
                used.add(object_name)

        if len(rows) < BOOKS_PAGE_SIZE:
            break
        offset += BOOKS_PAGE_SIZE

    return used


def list_storage_objects(prefix: str = "") -> list[str]:
    objects: list[str] = []
    offset = 0

    while True:
        rows = supabase.storage.from_(STORAGE_BUCKET).list(
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
                objects.extend(list_storage_objects(object_name))
            else:
                objects.append(object_name)

        if len(rows) < STORAGE_PAGE_SIZE:
            break
        offset += STORAGE_PAGE_SIZE

    return objects


def remove_objects(paths: list[str]) -> int:
    removed = 0
    for start in range(0, len(paths), DELETE_BATCH_SIZE):
        batch = paths[start:start + DELETE_BATCH_SIZE]
        supabase.storage.from_(STORAGE_BUCKET).remove(batch)
        removed += len(batch)
        print(f"🗑️  Đã xóa {removed}/{len(paths)} file...")
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description="Dọn ảnh bìa cũ trong Supabase Storage bucket covers.")
    parser.add_argument("--delete", action="store_true", help="Xóa thật các cover không còn được DB dùng.")
    parser.add_argument("--yes", action="store_true", help="Xác nhận xóa thật, bắt buộc đi kèm --delete.")
    parser.add_argument("--prefix", default="", help="Chỉ scan một prefix trong bucket covers.")
    parser.add_argument("--limit", type=int, default=None, help="Giới hạn số file orphan để report/xóa.")
    args = parser.parse_args()

    print("🔎 Đang đọc cover_url đang được dùng trong bảng books...")
    used = fetch_used_cover_names()

    print(f"🔎 Đang scan bucket '{STORAGE_BUCKET}'...")
    stored = list_storage_objects(args.prefix)
    orphaned = sorted(path for path in stored if path not in used)
    if args.limit is not None:
        orphaned = orphaned[:args.limit]

    used_in_storage = sum(1 for path in stored if path in used)

    print("\n📊 Kết quả:")
    print(f"   Cover đang được DB dùng       : {len(used)}")
    print(f"   File trong bucket covers      : {len(stored)}")
    print(f"   File trong bucket còn được dùng: {used_in_storage}")
    print(f"   File orphan có thể dọn        : {len(orphaned)}")

    if orphaned:
        print("\nMột số file orphan:")
        for path in orphaned[:30]:
            print(f"   - {path}")
        if len(orphaned) > 30:
            print(f"   ... còn {len(orphaned) - 30} file nữa")

    if not args.delete:
        print("\n✅ Dry-run xong. Chưa xóa file nào.")
        print("   Muốn xóa thật, chạy: python cleanup_orphan_covers.py --delete --yes")
        return

    if not args.yes:
        print("\n❌ Để xóa thật cần thêm --yes.")
        return

    if not orphaned:
        print("\n✅ Không có file orphan để xóa.")
        return

    print("\n🚨 Bắt đầu xóa file orphan...")
    removed = remove_objects(orphaned)
    print(f"✅ Hoàn tất. Đã xóa {removed} file cover cũ.")


if __name__ == "__main__":
    main()
