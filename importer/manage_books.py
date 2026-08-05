"""
manage_books.py — Công cụ quản lý truyện trên Database

Lưu ý: "Tên Truyện" = title= trong file book_info.txt (không phải tên folder).
Dùng lệnh 'list' để xem đúng tên.

Các lệnh:
  python manage_books.py list
      → Liệt kê tất cả truyện trong DB

  python manage_books.py list-chapters "Tên Truyện"
      → Xem danh sách chương của một truyện

  python manage_books.py delete-chapter "Tên Truyện" 5
      → Xóa chương số 5 của truyện

  python manage_books.py delete-chapter "Tên Truyện" 5 6 10
      → Xóa chương 5, 6, 10 cùng lúc

  python manage_books.py delete-book "Tên Truyện"
      → Xóa truyện và toàn bộ chương

  python manage_books.py delete-chapters "Tên Truyện"
      → Chỉ xóa toàn bộ chương, giữ lại thông tin truyện

  python manage_books.py resync --translated-dir chapters/Ten_Truyen_Translated
      → Xóa toàn bộ chương rồi upload lại từ đầu

  python manage_books.py resync-all
      → Xóa và đồng bộ lại TẤT CẢ truyện từ thư mục chapters/
"""

import os
import sys
import re
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client
import markdown

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ Thiếu SUPABASE_URL hoặc SUPABASE_KEY trong file .env")
    sys.exit(1)

supabase: Client = create_client(url, key)

STORAGE_BUCKET = "covers"
CONTENT_STORAGE_BUCKET = "chapter-content"
DEFAULT_COVER = "https://images.unsplash.com/photo-1541963463532-d68292c34b19?w=300&q=80"
UPLOADABLE_DIR_SUFFIXES = ("_Translated", "_Convert")


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def safe_storage_name(value: str) -> str:
    safe_name = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()
    return safe_name[:80] or "chapter"


def find_book_by_title(title: str):
    res = supabase.table("books").select("id, title, chapter_count").eq("title", title).execute()
    return res.data[0] if res.data else None


def find_book_by_id(book_id: int):
    res = supabase.table("books").select("id, title, chapter_count").eq("id", book_id).execute()
    return res.data[0] if res.data else None


def read_book_info(translated_dir: str):
    """Đọc title và author từ book_info.txt trong thư mục translated."""
    title, author = "Chưa đặt tên", "Chưa rõ"
    info_path = os.path.join(translated_dir, "book_info.txt")
    if os.path.exists(info_path):
        with open(info_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("title="):
                    title = line.split("=", 1)[1].strip()
                elif line.startswith("author="):
                    author = line.split("=", 1)[1].strip()
    return title, author


def upload_cover(translated_dir: str, book_title: str) -> str:
    theme_path = os.path.join(translated_dir, "theme.png")
    if not os.path.exists(theme_path):
        return DEFAULT_COVER
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", book_title).lower() + ".png"
    try:
        with open(theme_path, "rb") as f:
            image_bytes = f.read()
        try:
            supabase.storage.from_(STORAGE_BUCKET).remove([safe_name])
        except Exception:
            pass
        supabase.storage.from_(STORAGE_BUCKET).upload(
            safe_name, image_bytes, {"content-type": "image/png"}
        )
        return supabase.storage.from_(STORAGE_BUCKET).get_public_url(safe_name)
    except Exception as e:
        print(f"⚠️  Lỗi upload ảnh: {e}")
        return DEFAULT_COVER


def upload_chapter_content(book_id: int, chapter_number: int, chapter_title: str, html_content: str) -> tuple[str, str]:
    """Upload nội dung chương lên Storage. Trả về (content_path, public_url)."""
    safe_title = safe_storage_name(chapter_title)
    content_path = f"{book_id}/{chapter_number:04d}_{safe_title}.html"
    try:
        try:
            supabase.storage.from_(CONTENT_STORAGE_BUCKET).remove([content_path])
        except Exception:
            pass
        supabase.storage.from_(CONTENT_STORAGE_BUCKET).upload(
            content_path,
            html_content.encode("utf-8"),
            {
                "content-type": "text/html; charset=utf-8",
                "cache-control": "3600"
            }
        )
        return content_path, supabase.storage.from_(CONTENT_STORAGE_BUCKET).get_public_url(content_path)
    except Exception as e:
        print(f"❌ Lỗi upload nội dung chương {chapter_number}: {e}")
        print(f"   Gợi ý: Hãy tạo bucket '{CONTENT_STORAGE_BUCKET}' (Public) trong Supabase Storage.")
        raise


def validate_content_storage_setup():
    try:
        supabase.table("chapters").select("id, content_path, content_url").limit(1).execute()
    except Exception as e:
        print("❌ Bảng chapters chưa có cột content_path/content_url.")
        print("   Hãy chạy SQL trong README trước khi upload hoặc resync.")
        raise e

    try:
        supabase.storage.from_(CONTENT_STORAGE_BUCKET).list("", {"limit": 1})
    except Exception as e:
        print(f"❌ Không truy cập được bucket Storage '{CONTENT_STORAGE_BUCKET}'.")
        print(f"   Hãy tạo bucket '{CONTENT_STORAGE_BUCKET}' và đặt Public trong Supabase Storage.")
        raise e


def delete_chapter_content_paths(paths: list[str]):
    """Xóa file nội dung chương trên Storage theo danh sách path, bỏ qua lỗi để không chặn DB cleanup."""
    paths = [path for path in paths if path]
    if not paths:
        return
    try:
        supabase.storage.from_(CONTENT_STORAGE_BUCKET).remove(paths)
    except Exception as e:
        print(f"⚠️  Không xóa được một số file nội dung trên Storage: {e}")


def delete_book_content_files(book_id: int):
    """Xóa toàn bộ file nội dung chương của một truyện trên Storage."""
    try:
        files = supabase.storage.from_(CONTENT_STORAGE_BUCKET).list(str(book_id))
        paths = [
            f"{book_id}/{item['name']}"
            for item in files
            if item.get("name")
        ]
        delete_chapter_content_paths(paths)
    except Exception as e:
        print(f"⚠️  Không dọn được thư mục nội dung Storage của book ID={book_id}: {e}")


def upload_all_chapters(book_id: int, translated_dir: str):
    """Upload toàn bộ chương từ thư mục vào DB (không kiểm tra trùng)."""
    validate_content_storage_setup()

    files = sorted([f for f in os.listdir(translated_dir) if f.endswith(".md")])
    if not files:
        print("⚠️  Không tìm thấy file .md nào.")
        return 0

    chapters = []
    for filename in files:
        match = re.match(r"^(\d+)_", filename)
        if not match:
            continue
        chapter_number = int(match.group(1))
        file_path = os.path.join(translated_dir, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            md_content = f.read()
        title_match = re.search(r"^#\s+(.+)$", md_content, flags=re.MULTILINE)
        chapter_title = title_match.group(1).strip() if title_match else f"Chương {chapter_number}"
        html_content = markdown.markdown(md_content)
        content_path, content_url = upload_chapter_content(
            book_id,
            chapter_number,
            chapter_title,
            html_content
        )
        chapters.append({
            "book_id": book_id,
            "title": chapter_title,
            "content_html": "",
            "content_path": content_path,
            "content_url": content_url,
            "chapter_number": chapter_number,
        })

    total = 0
    for i in range(0, len(chapters), 50):
        batch = chapters[i:i + 50]
        supabase.table("chapters").insert(batch).execute()
        total += len(batch)
        print(f"   📦 Đã đẩy {min(i + 50, len(chapters))}/{len(chapters)} chương...")

    # Cập nhật chapter_count
    res = supabase.table("chapters").select("id", count="exact").eq("book_id", book_id).execute()
    supabase.table("books").update({"chapter_count": res.count}).eq("id", book_id).execute()
    return total


# ─────────────────────────────────────────
# Commands
# ─────────────────────────────────────────

def cmd_list():
    """Liệt kê tất cả truyện trong DB."""
    res = supabase.table("books").select("id, title, author, chapter_count, status").order("id").execute()
    books = res.data
    if not books:
        print("📭 Chưa có truyện nào trong Database.")
        return
    print(f"\n{'ID':<6} {'Tên Truyện':<40} {'Tác Giả':<20} {'Chương':<8} {'TT'}")
    print("─" * 85)
    for b in books:
        print(f"{b['id']:<6} {b['title']:<40} {(b['author'] or 'Chưa rõ'):<20} {(b['chapter_count'] or 0):<8} {b['status'] or ''}")
    print(f"\n✅ Tổng cộng: {len(books)} truyện")


def cmd_delete_book(title: str, confirm: bool = False):
    """Xóa truyện và toàn bộ chương."""
    book = find_book_by_title(title)
    if not book:
        print(f"❌ Không tìm thấy truyện: '{title}'")
        return

    print(f"\n⚠️  SẮP XÓA: [{book['id']}] {book['title']} ({book['chapter_count']} chương)")

    if not confirm:
        ans = input("Xác nhận xóa? (yes/no): ").strip().lower()
        if ans != "yes":
            print("❌ Hủy bỏ.")
            return

    delete_book_content_files(book["id"])
    # Xóa chương trước
    supabase.table("chapters").delete().eq("book_id", book["id"]).execute()
    # Xóa truyện
    supabase.table("books").delete().eq("id", book["id"]).execute()
    print(f"🗑️  Đã xóa truyện '{book['title']}' và toàn bộ chương.")


def cmd_list_chapters(title: str):
    """Liệt kê danh sách chương của một truyện."""
    book = find_book_by_title(title)
    if not book:
        print(f"❌ Không tìm thấy truyện: '{title}'")
        print("   Gợi ý: Chạy 'python manage_books.py list' để xem đúng tên.")
        return

    res = supabase.table("chapters") \
        .select("chapter_number, title") \
        .eq("book_id", book["id"]) \
        .order("chapter_number") \
        .execute()

    chapters = res.data
    if not chapters:
        print(f"📭 Truyện '{title}' chưa có chương nào trong DB.")
        return

    print(f"\n📚 [{book['id']}] {book['title']} — {len(chapters)} chương")
    print(f"{'Số':<8} {'Tên Chương'}")
    print("─" * 60)
    for ch in chapters:
        print(f"{ch['chapter_number']:<8} {ch['title']}")


def cmd_delete_chapter(title: str, chapter_nums: list, confirm: bool = False):
    """Xóa một hoặc nhiều chương cụ thể của truyện."""
    book = find_book_by_title(title)
    if not book:
        print(f"❌ Không tìm thấy truyện: '{title}'")
        print("   Gợi ý: Chạy 'python manage_books.py list' để xem đúng tên.")
        return

    # Kiểm tra từng chương có tồn tại không
    found = []
    not_found = []
    for num in chapter_nums:
        res = supabase.table("chapters") \
            .select("id, chapter_number, title, content_path") \
            .eq("book_id", book["id"]) \
            .eq("chapter_number", num) \
            .execute()
        if res.data:
            found.append(res.data[0])
        else:
            not_found.append(num)

    if not_found:
        print(f"⚠️  Không tìm thấy chương số: {', '.join(map(str, not_found))}")

    if not found:
        print("❌ Không có chương nào để xóa.")
        return

    print(f"\n⚠️  SẮP XÓA {len(found)} chương của truyện '{book['title']}':")
    for ch in found:
        print(f"   Chương {ch['chapter_number']}: {ch['title']}")

    if not confirm:
        ans = input("\nXác nhận xóa? (yes/no): ").strip().lower()
        if ans != "yes":
            print("❌ Hủy bỏ.")
            return

    for ch in found:
        supabase.table("chapters").delete().eq("id", ch["id"]).execute()
        delete_chapter_content_paths([ch.get("content_path")])
        print(f"🗑️  Đã xóa: Chương {ch['chapter_number']} — {ch['title']}")

    # Cập nhật lại chapter_count
    res = supabase.table("chapters").select("id", count="exact").eq("book_id", book["id"]).execute()
    supabase.table("books").update({"chapter_count": res.count}).eq("id", book["id"]).execute()
    print(f"\n✅ Xóa xong. Tổng còn lại: {res.count} chương.")


def cmd_delete_chapters(title: str, confirm: bool = False):
    """Chỉ xóa toàn bộ chương, giữ lại thông tin truyện."""
    book = find_book_by_title(title)
    if not book:
        print(f"❌ Không tìm thấy truyện: '{title}'")
        return

    print(f"\n⚠️  SẮP XÓA {book['chapter_count']} chương của: {book['title']}")

    if not confirm:
        ans = input("Xác nhận xóa? (yes/no): ").strip().lower()
        if ans != "yes":
            print("❌ Hủy bỏ.")
            return

    delete_book_content_files(book["id"])
    supabase.table("chapters").delete().eq("book_id", book["id"]).execute()
    supabase.table("books").update({"chapter_count": 0}).eq("id", book["id"]).execute()
    print(f"🗑️  Đã xóa toàn bộ chương. Thông tin truyện vẫn còn trong DB.")


def cmd_resync(translated_dir: str, force: bool = False):
    """Xóa toàn bộ chương cũ rồi upload lại từ thư mục."""
    if not os.path.isdir(translated_dir):
        print(f"❌ Không tìm thấy thư mục: {translated_dir}")
        return

    title, author = read_book_info(translated_dir)
    book = find_book_by_title(title)

    print(f"\n🔄 RESYNC: {title}")

    if book:
        if not force:
            ans = input(f"Xóa {book['chapter_count']} chương cũ và upload lại? (yes/no): ").strip().lower()
            if ans != "yes":
                print("❌ Hủy bỏ.")
                return
        # Xóa tất cả chương cũ
        delete_book_content_files(book["id"])
        supabase.table("chapters").delete().eq("book_id", book["id"]).execute()
        supabase.table("books").update({"chapter_count": 0}).eq("id", book["id"]).execute()
        print(f"🗑️  Đã xóa chương cũ của '{title}'")
        book_id = book["id"]
    else:
        # Tạo mới
        cover_url = upload_cover(translated_dir, title)
        res = supabase.table("books").insert({
            "title": title, "author": author,
            "status": "Đang ra", "rating": 8.0,
            "chapter_count": 0, "cover_url": cover_url
        }).execute()
        book_id = res.data[0]["id"]
        print(f"✅ Đã tạo truyện mới (ID={book_id})")

    # Upload lại
    cover_url = upload_cover(translated_dir, title)
    supabase.table("books").update({"cover_url": cover_url}).eq("id", book_id).execute()

    total = upload_all_chapters(book_id, translated_dir)
    print(f"🎉 Resync hoàn tất: {total} chương đã được upload lại.")


def cmd_resync_all(scan_dir: str = "chapters", force: bool = False):
    """Resync tất cả thư mục *_Translated hoặc *_Convert trong scan_dir."""
    translated_dirs = sorted([
        os.path.join(scan_dir, d)
        for d in os.listdir(scan_dir)
        if os.path.isdir(os.path.join(scan_dir, d)) and d.endswith(UPLOADABLE_DIR_SUFFIXES)
    ])
    if not translated_dirs:
        print(f"⚠️  Không tìm thấy thư mục nào trong '{scan_dir}'")
        return

    print(f"\n📚 Sẽ resync {len(translated_dirs)} bộ truyện:")
    for i, d in enumerate(translated_dirs, 1):
        print(f"   {i}. {d}")

    if not force:
        ans = input(f"\nXác nhận resync tất cả {len(translated_dirs)} truyện? (yes/no): ").strip().lower()
        if ans != "yes":
            print("❌ Hủy bỏ.")
            return

    for d in translated_dirs:
        print(f"\n{'='*60}")
        cmd_resync(d, force=True)

    print(f"\n{'='*60}")
    print(f"🏆 Đã resync xong tất cả {len(translated_dirs)} bộ truyện!")


# ─────────────────────────────────────────
# Main
# ─────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quản lý truyện trên Database.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="Liệt kê tất cả truyện trong DB")

    # list-chapters
    p_lc = subparsers.add_parser("list-chapters", help="Xem danh sách chương của một truyện")
    p_lc.add_argument("title", help="Tên truyện")

    # delete-chapter (một hoặc nhiều chương)
    p_dc = subparsers.add_parser("delete-chapter", help="Xóa một hoặc nhiều chương cụ thể")
    p_dc.add_argument("title", help="Tên truyện")
    p_dc.add_argument("chapters", nargs="+", type=int,
                      help="Số chương cần xóa (ví dụ: 5 hoặc 5 6 10)")
    p_dc.add_argument("--yes", action="store_true", help="Bỏ qua xác nhận")

    # delete-book
    p_del = subparsers.add_parser("delete-book", help="Xóa truyện và toàn bộ chương")
    p_del.add_argument("title", help="Tên truyện")
    p_del.add_argument("--yes", action="store_true", help="Bỏ qua xác nhận")

    # delete-chapters (toàn bộ)
    p_delc = subparsers.add_parser("delete-chapters", help="Xóa toàn bộ chương, giữ info truyện")
    p_delc.add_argument("title", help="Tên truyện")
    p_delc.add_argument("--yes", action="store_true", help="Bỏ qua xác nhận")

    # resync
    p_resync = subparsers.add_parser("resync", help="Xóa chương cũ và upload lại từ thư mục")
    p_resync.add_argument("--translated-dir", required=True, help="Thư mục chứa file .md đã dịch")
    p_resync.add_argument("--yes", action="store_true", help="Bỏ qua xác nhận")

    # resync-all
    p_ra = subparsers.add_parser("resync-all", help="Resync tất cả truyện trong chapters/")
    p_ra.add_argument("--scan-dir", default="chapters", help="Thư mục chứa các *_Translated")
    p_ra.add_argument("--yes", action="store_true", help="Bỏ qua xác nhận")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list()
    elif args.command == "list-chapters":
        cmd_list_chapters(args.title)
    elif args.command == "delete-chapter":
        cmd_delete_chapter(args.title, args.chapters, confirm=args.yes)
    elif args.command == "delete-book":
        cmd_delete_book(args.title, confirm=args.yes)
    elif args.command == "delete-chapters":
        cmd_delete_chapters(args.title, confirm=args.yes)
    elif args.command == "resync":
        cmd_resync(args.translated_dir, force=args.yes)
    elif args.command == "resync-all":
        cmd_resync_all(args.scan_dir, force=args.yes)
