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
    print("❌ Lỗi: Bạn cần điền SUPABASE_URL và SUPABASE_KEY trong file .env")
    sys.exit(1)

supabase: Client = create_client(url, key)

SUPABASE_URL_BASE = url
STORAGE_BUCKET = "covers"
DEFAULT_COVER = "https://images.unsplash.com/photo-1541963463532-d68292c34b19?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80"


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


def get_or_create_book(title, author, cover_url=DEFAULT_COVER):
    # Kiểm tra xem truyện đã có trên DB chưa
    res = supabase.table("books").select("id").eq("title", title).execute()
    if len(res.data) > 0:
        book_id = res.data[0]['id']
        print(f"🔍 Đã tìm thấy truyện '{title}' trên Database (ID: {book_id})")
        # Cập nhật cover_url nếu đã có ảnh mới
        if cover_url != DEFAULT_COVER:
            supabase.table("books").update({"cover_url": cover_url}).eq("id", book_id).execute()
            print(f"🖼️  Đã cập nhật ảnh bìa mới cho truyện ID={book_id}")
        return book_id

    print(f"🚀 Chưa có truyện '{title}'. Đang tạo mới...")
    book_data = {
        "title": title,
        "author": author,
        "status": "Đang ra",
        "rating": 8.0,
        "chapter_count": 0,
        "cover_url": cover_url
    }
    res = supabase.table("books").insert(book_data).execute()
    book_id = res.data[0]['id']
    print(f"✅ Đã tạo truyện mới với ID = {book_id}")
    return book_id

def upload_chapters(translated_dir):
    print(f"📖 Đang đọc các chương từ: {translated_dir}")

    # Lấy thông tin truyện từ book_info.txt trong thư mục Translated
    book_title = "Chưa đặt tên"
    book_author = "Chưa rõ"
    info_path = os.path.join(translated_dir, "book_info.txt")

    if os.path.exists(info_path):
        with open(info_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("title="):
                    book_title = line.split("=", 1)[1].strip()
                elif line.startswith("author="):
                    book_author = line.split("=", 1)[1].strip()
    else:
        print("⚠️  Không tìm thấy book_info.txt — dùng tiêu đề mặc định.")

    cover_url = upload_cover_image(translated_dir, book_title)
    book_id = get_or_create_book(book_title, book_author, cover_url)
    
    # Đọc danh sách các chương đã dịch
    files = sorted([f for f in os.listdir(translated_dir) if f.endswith(".md")])
    if not files:
        print("⚠️ Không tìm thấy file .md nào trong thư mục dịch.")
        return

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
            
        chapters_to_insert.append({
            "book_id": book_id,
            "title": chapter_title,
            "content_html": html_content,
            "chapter_number": chapter_number
        })
        
    if not chapters_to_insert:
        print("✅ Tất cả các chương hiện tại đều đã được upload lên DB.")
        return
        
    print(f"📦 Đang đẩy {len(chapters_to_insert)} chương mới lên DB...")
    
    # Chia nhỏ mỗi lần upload 50 chương
    for i in range(0, len(chapters_to_insert), 50):
        batch = chapters_to_insert[i:i+50]
        supabase.table("chapters").insert(batch).execute()
        print(f"  Đã đẩy {min(i+50, len(chapters_to_insert))}/{len(chapters_to_insert)} chương...")
        
    # Cập nhật tổng số lượng chương
    res = supabase.table("chapters").select("id", count="exact").eq("book_id", book_id).execute()
    total_chapters = res.count
    supabase.table("books").update({"chapter_count": total_chapters}).eq("id", book_id).execute()
    
    print("🎉 Quá trình Upload lên Web hoàn tất!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Công cụ đẩy các file Markdown truyện đã dịch lên Database.')
    parser.add_argument('--translated-dir', default="chapters/Xich_Tam_Tuan_Thien_Translated", help='Thư mục chứa các file .md đã dịch, theme.png và book_info.txt')
    args = parser.parse_args()

    upload_chapters(args.translated_dir)
