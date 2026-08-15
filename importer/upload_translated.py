import os
import sys
import re
import argparse
import gzip
import time
from dotenv import load_dotenv
from supabase import create_client, Client
import markdown

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ Lỗi: Bạn cần điền SUPABASE_URL và SUPABASE_KEY trong file .env")
    sys.exit(1)

supabase: Client = create_client(url, key)

SUPABASE_URL_BASE = url
STORAGE_BUCKET = "covers"
CONTENT_STORAGE_BUCKET = "chapter-content"
DEFAULT_COVER = "https://images.unsplash.com/photo-1541963463532-d68292c34b19?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80"
UPLOADABLE_DIR_SUFFIX = "_Translated"
CHAPTER_INSERT_BATCH_SIZE = 50
UPLOAD_RETRY_COUNT = 3


def safe_storage_name(value: str) -> str:
    safe_name = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()
    return safe_name[:80] or "chapter"


def upload_cover_image(translated_dir: str, book_title: str) -> str:
    """Upload theme.png từ thư mục Translated lên Supabase Storage. Trả về public URL."""
    theme_path = os.path.join(translated_dir, "theme.png")
    if not os.path.exists(theme_path):
        print("ℹ️  Không tìm thấy theme.png — dùng ảnh mặc định.")
        return DEFAULT_COVER

    # Tên file trên Storage: slug tên truyện
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", book_title).lower() + ".png"

    try:
        with open(theme_path, "rb") as f:
            image_bytes = f.read()
        # Xóa file cũ nếu đã tồn tại (upsert)
        try:
            supabase.storage.from_(STORAGE_BUCKET).remove([safe_name])
        except Exception:
            pass
        supabase.storage.from_(STORAGE_BUCKET).upload(
            safe_name,
            image_bytes,
            {"content-type": "image/png"}
        )
        public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(safe_name)
        print(f"🖼️  Đã upload ảnh bìa: {public_url}")
        return public_url
    except Exception as e:
        print(f"⚠️  Lỗi upload ảnh bìa: {e}")
        print("   Gợi ý: Hãy tạo bucket 'covers' (Public) trong Supabase Storage.")
        return DEFAULT_COVER


def upload_chapter_content(book_id: int, chapter_number: int, chapter_title: str, html_content: str) -> tuple[str, str]:
    """Upload nội dung chương lên Storage. Trả về (content_path, public_url)."""
    safe_title = safe_storage_name(chapter_title)
    content_path = f"{book_id}/{chapter_number:04d}_{safe_title}.html.gz"

    compressed_html = gzip.compress(html_content.encode("utf-8"), compresslevel=9)
    last_error = None

    for attempt in range(1, UPLOAD_RETRY_COUNT + 1):
        try:
            try:
                supabase.storage.from_(CONTENT_STORAGE_BUCKET).remove([content_path])
            except Exception:
                pass

            supabase.storage.from_(CONTENT_STORAGE_BUCKET).upload(
                content_path,
                compressed_html,
                {
                    "content-type": "application/gzip",
                    "cache-control": "3600"
                }
            )
            public_url = supabase.storage.from_(CONTENT_STORAGE_BUCKET).get_public_url(content_path)
            return content_path, public_url
        except Exception as e:
            last_error = e
            if attempt < UPLOAD_RETRY_COUNT:
                wait_seconds = attempt * 3
                print(f"⚠️  Upload chương {chapter_number} lỗi lần {attempt}/{UPLOAD_RETRY_COUNT}: {e}")
                print(f"   Chờ {wait_seconds}s rồi thử lại...")
                time.sleep(wait_seconds)

    print(f"❌ Lỗi upload nội dung chương {chapter_number}: {last_error}")
    print("   Đây thường là lỗi mạng/Supabase Storage timeout. Chạy lại script để tiếp tục từ chương còn thiếu.")
    raise last_error


def validate_content_storage_setup():
    try:
        supabase.table("chapters").select("id, content_path, content_url").limit(1).execute()
    except Exception as e:
        print("❌ Bảng chapters chưa có cột content_path/content_url.")
        print("   Hãy chạy SQL trong README trước khi upload.")
        raise e

    try:
        supabase.storage.from_(CONTENT_STORAGE_BUCKET).list("", {"limit": 1})
    except Exception as e:
        print(f"❌ Không truy cập được bucket Storage '{CONTENT_STORAGE_BUCKET}'.")
        print(f"   Hãy tạo bucket '{CONTENT_STORAGE_BUCKET}' và đặt Public trong Supabase Storage.")
        raise e


def read_book_info(translated_dir: str) -> dict:
    """Đọc metadata từ book_info.txt."""
    book_info = {
        "title": "Chưa đặt tên",
        "author": "Chưa rõ",
        "status": "Đang ra",
        "description": "",
        "genres": "",
        "source_type": "",
    }
    info_path = os.path.join(translated_dir, "book_info.txt")

    if os.path.exists(info_path):
        with open(info_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                if key in book_info:
                    book_info[key] = value.strip() or book_info[key]
    else:
        print("⚠️  Không tìm thấy book_info.txt — dùng tiêu đề mặc định.")

    return book_info


def get_or_create_book(book_info: dict, cover_url=DEFAULT_COVER):
    title = book_info["title"]
    author = book_info["author"]

    # Kiểm tra xem truyện đã có trên DB chưa
    res = supabase.table("books").select("id").eq("title", title).execute()
    if len(res.data) > 0:
        book_id = res.data[0]['id']
        print(f"🔍 Đã tìm thấy truyện '{title}' trên Database (ID: {book_id})")
        update_data = {
            "author": author,
            "status": book_info["status"],
            "description": book_info["description"],
            "genres": book_info["genres"],
            "source_type": book_info["source_type"],
        }
        if cover_url != DEFAULT_COVER:
            update_data["cover_url"] = cover_url
        supabase.table("books").update(update_data).eq("id", book_id).execute()
        print(f"ℹ️  Đã cập nhật metadata: {book_info['status']}")
        if cover_url != DEFAULT_COVER:
            print(f"🖼️  Đã cập nhật ảnh bìa mới cho truyện ID={book_id}")
        return book_id

    print(f"🚀 Chưa có truyện '{title}'. Đang tạo mới...")
    book_data = {
        "title": title,
        "author": author,
        "status": book_info["status"],
        "description": book_info["description"],
        "genres": book_info["genres"],
        "source_type": book_info["source_type"],
        "rating": 8.0,
        "chapter_count": 0,
        "cover_url": cover_url
    }
    res = supabase.table("books").insert(book_data).execute()
    book_id = res.data[0]['id']
    print(f"✅ Đã tạo truyện mới với ID = {book_id}")
    return book_id

def upload_chapters(translated_dir, limit: int | None = None):
    print(f"📖 Đang đọc các chương từ: {translated_dir}")

    if not os.path.isdir(translated_dir):
        print(f"❌ Không tìm thấy thư mục: {translated_dir}")
        return

    files = sorted([f for f in os.listdir(translated_dir) if f.endswith(".md")])
    if limit is not None:
        files = files[:limit]
        print(f"🧪 Chế độ upload thử: chỉ xử lý {len(files)} chương đầu.")

    if not files:
        print("⚠️ Không tìm thấy file .md nào trong thư mục dịch. Dừng trước khi tạo/cập nhật truyện.")
        return

    validate_content_storage_setup()

    # Lấy thông tin truyện từ book_info.txt trong thư mục Translated
    book_info = read_book_info(translated_dir)

    cover_url = upload_cover_image(translated_dir, book_info["title"])
    book_id = get_or_create_book(book_info, cover_url)

    chapters_to_insert = []
    inserted_count = 0
    failed_chapter = None

    def flush_chapter_batch():
        nonlocal chapters_to_insert, inserted_count
        if not chapters_to_insert:
            return
        supabase.table("chapters").insert(chapters_to_insert).execute()
        inserted_count += len(chapters_to_insert)
        print(f"  📦 Đã ghi {inserted_count} chương mới vào DB...")
        chapters_to_insert = []
    
    for filename in files:
        # Lấy số chương từ tên file (ví dụ: 0001_Xich_Tam_Tuan_Thien.md -> 1)
        match = re.match(r"^(\d+)_", filename)
        if not match:
            continue
        chapter_number = int(match.group(1))
        
        file_path = os.path.join(translated_dir, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            md_content = f.read()
            
        # Tìm tiêu đề chương từ thẻ H1 đầu tiên (nếu có)
        title_match = re.search(r"^#\s+(.+)$", md_content, flags=re.MULTILINE)
        if title_match:
            chapter_title = title_match.group(1).strip()
        else:
            chapter_title = f"Chương {chapter_number}"
            
        # Chuyển đổi Markdown sang HTML để tương thích với cấu trúc của web
        html_content = markdown.markdown(md_content)
        
        # Kiểm tra xem chương này đã tồn tại trên DB chưa để tránh trùng lặp
        res = supabase.table("chapters").select("id").eq("book_id", book_id).eq("chapter_number", chapter_number).execute()
        if len(res.data) > 0:
            print(f"[-] Bỏ qua Chương {chapter_number}: Đã có trên Database.")
            continue

        try:
            content_path, content_url = upload_chapter_content(
                book_id,
                chapter_number,
                chapter_title,
                html_content
            )
        except Exception:
            failed_chapter = chapter_number
            break
            
        chapters_to_insert.append({
            "book_id": book_id,
            "title": chapter_title,
            "content_html": "",
            "content_path": content_path,
            "content_url": content_url,
            "chapter_number": chapter_number
        })

        if len(chapters_to_insert) >= CHAPTER_INSERT_BATCH_SIZE:
            flush_chapter_batch()

    flush_chapter_batch()
        
    if inserted_count == 0 and failed_chapter is None:
        print("✅ Tất cả các chương hiện tại đều đã được upload lên DB.")
        return
        
    # Cập nhật tổng số lượng chương
    res = supabase.table("chapters").select("id", count="exact").eq("book_id", book_id).execute()
    total_chapters = res.count
    supabase.table("books").update({"chapter_count": total_chapters}).eq("id", book_id).execute()

    if failed_chapter is not None:
        print(f"⚠️  Dừng ở Chương {failed_chapter} do lỗi upload Storage.")
        print(f"   Đã lưu DB các batch trước đó. Tổng chương hiện có trong DB: {total_chapters}.")
        print("   Hãy chạy lại cùng lệnh, script sẽ bỏ qua chương đã có và tiếp tục phần còn lại.")
        return
    
    print("🎉 Quá trình Upload lên Web hoàn tất!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Công cụ đẩy các file Markdown truyện đã dịch lên Database.',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--translated-dir',
        default=None,
        help='Thư mục chứa file .md đã dịch của MỘT truyện (ví dụ: chapters/Xich_Tam_Tuan_Thien_Translated)'
    )
    parser.add_argument(
        '--scan-dir',
        default="chapters",
        help='Thư mục cha để tự động tìm tất cả thư mục *_Translated bên trong.\n'
             'Mặc định: chapters/  (bỏ qua nếu đã truyền --translated-dir)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Chỉ upload N file .md đầu tiên trong mỗi thư mục. Dùng để test trước khi upload toàn bộ.'
    )
    args = parser.parse_args()

    if args.translated_dir:
        # Upload 1 truyện cụ thể
        upload_chapters(args.translated_dir, limit=args.limit)
    else:
        # Tự động quét và upload tất cả thư mục *_Translated
        scan_root = args.scan_dir
        if not os.path.isdir(scan_root):
            print(f"❌ Không tìm thấy thư mục: {scan_root}")
            sys.exit(1)

        translated_dirs = sorted([
            os.path.join(scan_root, d)
            for d in os.listdir(scan_root)
            if os.path.isdir(os.path.join(scan_root, d)) and d.endswith(UPLOADABLE_DIR_SUFFIX)
        ])

        if not translated_dirs:
            print(f"⚠️  Không tìm thấy thư mục nào kết thúc bằng '{UPLOADABLE_DIR_SUFFIX}' trong '{scan_root}'")
            sys.exit(1)

        print(f"\n📚 Tìm thấy {len(translated_dirs)} bộ truyện cần upload:")
        for i, d in enumerate(translated_dirs, 1):
            print(f"   {i}. {d}")
        print()

        for d in translated_dirs:
            print(f"\n{'='*60}")
            upload_chapters(d, limit=args.limit)

        print(f"\n{'='*60}")
        print(f"🏆 Đã xử lý xong tất cả {len(translated_dirs)} bộ truyện!")
