import os
import sys
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re

# Khởi tạo biến môi trường từ file .env
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ Lỗi: Bạn cần tạo file .env và điền SUPABASE_URL, SUPABASE_KEY")
    sys.exit(1)

# Khởi tạo kết nối tới Supabase
supabase: Client = create_client(url, key)

def import_epub(file_path):
    print(f"📖 Đang đọc file: {file_path}")
    try:
        book = epub.read_epub(file_path)
    except Exception as e:
        print(f"❌ Không thể đọc file Epub: {e}")
        return

    # 1. Trích xuất Metadata (Tên truyện, Tác giả)
    title_metadata = book.get_metadata('DC', 'title')
    title = title_metadata[0][0] if title_metadata else "Chưa rõ tên truyện"
    
    author_metadata = book.get_metadata('DC', 'creator')
    author = author_metadata[0][0] if author_metadata else "Chưa rõ tác giả"
    
    print(f"🔍 Đã tìm thấy Truyện: '{title}' bởi tác giả '{author}'")
    
    # 2. Đưa thông tin truyện vào Database (Bảng `books`)
    book_data = {
        "title": title,
        "author": author,
        "status": "Hoàn thành",
        "rating": 8.5,
        "chapter_count": 0,
        # Hình bìa mặc định tạm thời, sau có thể xử lý trích xuất cover
        "cover_url": "https://images.unsplash.com/photo-1541963463532-d68292c34b19?ixlib=rb-1.2.1&auto=format&fit=crop&w=300&q=80"
    }
    
    print("🚀 Đang đẩy truyện lên cơ sở dữ liệu...")
    res = supabase.table("books").insert(book_data).execute()
    book_id = res.data[0]['id']
    print(f"✅ Truyện đã tạo thành công với ID = {book_id}")

    # 3. Quét tất cả các file trong Epub để tìm Chương truyện (Bảng `chapters`)
    chapters = []
    chapter_index = 1
    
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            # Dùng BeautifulSoup để dọn dẹp mã HTML
            soup = BeautifulSoup(item.get_body_content(), 'html.parser')
            
            # Cố gắng tìm thẻ tiêu đề H1, H2 hoặc H3
            title_tag = soup.find(['h1', 'h2', 'h3'])
            if title_tag:
                chapter_title = title_tag.text.strip()
            else:
                chapter_title = f"Chương {chapter_index}"
                
            # Lọc bỏ các trang như Mục Lục, Lời nói đầu (Tùy chọn)
            if "toc" in chapter_title.lower() or "mục lục" in chapter_title.lower():
                continue
                
            # Trích xuất phần thân (Body) của chương
            body_content = soup.body if soup.body else soup
            # Có thể strip style, scripts ở đây nếu cần thiết
            for tag in body_content(['script', 'style']):
                tag.decompose()
            
            chapters.append({
                "book_id": book_id,
                "title": chapter_title,
                "content_html": str(body_content),
                "chapter_number": chapter_index
            })
            chapter_index += 1
            
    print(f"📦 Tìm thấy {len(chapters)} chương. Đang tải lên DB...")
    
    # Do giới hạn kích thước gói dữ liệu, chia nhỏ mỗi lần đẩy 50 chương
    for i in range(0, len(chapters), 50):
        batch = chapters[i:i+50]
        supabase.table("chapters").insert(batch).execute()
        print(f"  Đã đẩy {min(i+50, len(chapters))}/{len(chapters)} chương...")
        
    # 4. Cập nhật tổng số lượng chương vào bảng `books`
    supabase.table("books").update({"chapter_count": len(chapters)}).eq("id", book_id).execute()
    
    print("🎉 Quá trình import hoàn tất 100%!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Công cụ đọc EPUB và đẩy lên Database Supabase.')
    parser.add_argument('file', help='Đường dẫn (Path) tới file Ebook (EPUB)')
    args = parser.parse_args()
    
    if os.path.exists(args.file):
        import_epub(args.file)
    else:
        print(f"❌ Không tìm thấy file: {args.file}")
