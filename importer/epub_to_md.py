import sys
import os
import re
import unicodedata
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


def remove_viet_diacritics(text: str) -> str:
    """Chuyển đổi ký tự tiếng Việt có dấu thành không dấu."""
    # Thay thủ công chữ đ/Đ vì NFKD không xử lý được
    text = text.replace('đ', 'd').replace('Đ', 'D')
    result = unicodedata.normalize('NFKD', text)
    result = ''.join(c for c in result if not unicodedata.combining(c))
    return result


def sanitize_filename(name: str) -> str:
    """Loại bỏ dấu tiếng Việt và ký tự không hợp lệ trong tên file/folder."""
    name = remove_viet_diacritics(name)
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = name.strip().replace(' ', '_')
    name = re.sub(r'[^\w\-_.]', '', name)
    return name[:80]


def convert_to_chapters(epub_path: str, output_dir: str):
    print(f"📖 Đang đọc file: {epub_path}")
    try:
        book = epub.read_epub(epub_path)
    except Exception as e:
        print(f"❌ Không thể đọc file Epub: {e}")
        return

    # Lấy tên truyện và tác giả
    title_meta = book.get_metadata('DC', 'title')
    author_meta = book.get_metadata('DC', 'creator')
    title = title_meta[0][0] if title_meta else "Truyen_Khong_Ten"
    author = author_meta[0][0] if author_meta else "Chua_ro"

    print(f"🔍 Tên truyện : {title}")
    print(f"✍️  Tác giả    : {author}")

    # Tạo thư mục output riêng cho từng truyện
    book_folder = os.path.join(output_dir, sanitize_filename(title))
    os.makedirs(book_folder, exist_ok=True)

    # Lưu metadata truyện vào file riêng để importer dùng sau
    with open(os.path.join(book_folder, "book_info.txt"), 'w', encoding='utf-8') as f:
        f.write(f"title={title}\n")
        f.write(f"author={author}\n")

    chapter_index = 1
    skipped = 0

    for item in book.get_items():
        if item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue

        soup = BeautifulSoup(item.get_body_content(), 'html.parser')

        # Bỏ qua các trang không phải nội dung truyện
        title_tag = soup.find(['h1', 'h2', 'h3'])
        chapter_title = title_tag.text.strip() if title_tag else f"Chương {chapter_index}"

        lower_title = chapter_title.lower()
        if any(k in lower_title for k in ["toc", "mục lục", "cover", "bìa", "copyright"]):
            skipped += 1
            continue

        # Trích xuất đoạn văn sạch (chỉ giữ text, bỏ script/style)
        for tag in soup(['script', 'style']):
            tag.decompose()

        paragraphs = [p.get_text().strip() for p in soup.find_all('p') if p.get_text().strip()]

        if not paragraphs:
            skipped += 1
            continue

        # Tên file: 0001_Chuong_1_Ten_chuong.md
        file_name = f"{chapter_index:04d}_{sanitize_filename(chapter_title)}.md"
        file_path = os.path.join(book_folder, file_name)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# {chapter_title}\n\n")
            f.write("\n\n".join(paragraphs))

        print(f"  [{chapter_index:04d}] {chapter_title[:60]}")
        chapter_index += 1

    total = chapter_index - 1
    print(f"\n✅ Hoàn tất! Đã tách {total} chương → thư mục: {book_folder}")
    print(f"   (Bỏ qua {skipped} trang phụ không phải nội dung)")
    print(f"\n📌 Bước tiếp theo:")
    print(f"   1. Dịch từng file trong thư mục '{book_folder}/'")
    print(f"   2. Chạy importer.py để upload lên Database\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Cách dùng:")
        print("  1 file   : python epub_to_md.py <file.epub> [output_dir]")
        print("  Nhiều file: python epub_to_md.py <thu_muc_epub/> [output_dir]")
        print("")
        print("Ví dụ:")
        print("  python epub_to_md.py ~/Downloads/ebook.epub ./chapters")
        print("  python epub_to_md.py ~/Downloads/epubs/    ./chapters")
        sys.exit(1)

    input_path = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "./chapters"

    if not os.path.exists(input_path):
        print(f"❌ Không tìm thấy: {input_path}")
        sys.exit(1)

    # Nếu là THƯ MỤC → quét và xử lý tất cả file .epub bên trong
    if os.path.isdir(input_path):
        epub_files = [
            os.path.join(input_path, f)
            for f in sorted(os.listdir(input_path))
            if f.lower().endswith('.epub')
        ]
        if not epub_files:
            print(f"❌ Không tìm thấy file .epub nào trong: {input_path}")
            sys.exit(1)

        print(f"📚 Tìm thấy {len(epub_files)} file epub. Bắt đầu xử lý...\n")
        for i, epub_file in enumerate(epub_files, 1):
            print(f"══════ [{i}/{len(epub_files)}] {os.path.basename(epub_file)} ══════")
            convert_to_chapters(epub_file, out_dir)
            print()
        print(f"🏁 Xong! {len(epub_files)} truyện → thư mục: {out_dir}/")
        print(f"   Cấu trúc:")
        for f in sorted(os.listdir(out_dir)):
            print(f"   └── {f}/")

    # Nếu là FILE EPUB đơn lẻ
    elif input_path.lower().endswith('.epub'):
        convert_to_chapters(input_path, out_dir)

    else:
        print(f"❌ File không phải định dạng .epub: {input_path}")
