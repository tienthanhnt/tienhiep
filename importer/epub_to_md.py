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


def translated_folder_name(title: str) -> str:
    folder_name = sanitize_filename(title)
    if folder_name.lower().endswith("_translated"):
        return folder_name
    return f"{folder_name}_Translated"


def natural_sort_key(value: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', value)]


def is_skippable_title(title: str) -> bool:
    lower_title = title.lower()
    return any(k in lower_title for k in ["toc", "mục lục", "cover", "bìa", "copyright"])


def is_skippable_section(title: str, paragraphs) -> bool:
    if is_skippable_title(title):
        return True

    content = "\n".join(paragraphs).strip()
    lower_content = content.lower()
    if "mục lục" in lower_content and ("ebook tạo bởi" in lower_content or "giới thiệu" in lower_content):
        return True

    meaningful_text = re.sub(r'[-–—=~_•\soOo]+', '', content)
    return len(meaningful_text) < 40


CHAPTER_TITLE_RE = re.compile(r'^chương\s+\d+\b.*', re.IGNORECASE)
CHAPTER_RANGE_RE = re.compile(r'^chương\s+\d+\s*-\s*\d+\s*$', re.IGNORECASE)


def is_chapter_title_line(text: str) -> bool:
    line = text.strip()
    return bool(CHAPTER_TITLE_RE.match(line)) and not CHAPTER_RANGE_RE.match(line)


def is_chapter_range_line(text: str) -> bool:
    return bool(CHAPTER_RANGE_RE.match(text.strip()))


def is_output_chapter_title(text: str) -> bool:
    return is_chapter_title_line(text) or is_chapter_range_line(text)


def get_title_only_chapter_marker(soup: BeautifulSoup):
    lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]
    if len(lines) == 1 and is_output_chapter_title(lines[0]):
        return lines[0]
    return None


def get_chapter_number(title: str):
    match = re.match(r'^chương\s+(\d+)\b', title.strip(), re.IGNORECASE)
    return int(match.group(1)) if match else None


def get_chapter_sort_number(title: str, fallback: int) -> int:
    chapter_number = get_chapter_number(title)
    return chapter_number if chapter_number is not None else fallback


def normalize_title_text(text: str) -> str:
    text = remove_viet_diacritics(text).lower()
    return re.sub(r'\W+', '', text)


def get_chapter_subtitle(title: str) -> str:
    return title.split(":", 1)[1].strip() if ":" in title else ""


def collect_toc_chapter_titles(book):
    toc_titles = {}
    document_items = sorted(
        [item for item in book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT],
        key=lambda item: natural_sort_key(item.get_name()),
    )

    for item in document_items:
        soup = BeautifulSoup(item.get_body_content(), 'html.parser')
        lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]
        for line in lines:
            if not is_chapter_title_line(line) or ":" not in line:
                continue

            chapter_number = get_chapter_number(line)
            if chapter_number and chapter_number not in toc_titles:
                toc_titles[chapter_number] = line

    return toc_titles


def merge_pending_title_with_section(pending_title: str, section):
    title, paragraphs = section
    if not pending_title:
        return section

    if title != pending_title and not is_output_chapter_title(title):
        pending_subtitle = get_chapter_subtitle(pending_title)
        if pending_subtitle and normalize_title_text(pending_subtitle) == normalize_title_text(title):
            return (pending_title, paragraphs)
        return (f"{pending_title}: {title}", paragraphs)

    if title != pending_title or not paragraphs:
        return section

    first_line = paragraphs[0].strip()
    if is_output_chapter_title(first_line):
        return section

    if len(first_line) <= 160:
        return (f"{pending_title}: {first_line}", paragraphs[1:])

    return section


def split_lines_by_chapter_titles(lines, fallback_title: str):
    """Tách chương khi EPUB gộp nhiều tiêu đề Chương N trong text thường."""
    sections = []
    current_title = None
    current_paragraphs = []
    intro_lines = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if is_chapter_range_line(line):
            continue

        if is_chapter_title_line(line):
            if current_title and current_paragraphs:
                sections.append((current_title, current_paragraphs))
            current_title = line
            current_paragraphs = []
            continue

        if current_title:
            current_paragraphs.append(line)
        else:
            intro_lines.append(line)

    if current_title and current_paragraphs:
        sections.append((current_title, current_paragraphs))

    if sections:
        return sections

    return [(fallback_title, intro_lines)] if intro_lines else []


def split_embedded_chapters(title: str, paragraphs):
    lines = []
    for paragraph in paragraphs:
        lines.extend(paragraph.splitlines())

    embedded_sections = split_lines_by_chapter_titles(lines, title)
    if len(embedded_sections) > 1:
        return embedded_sections

    return [(title, paragraphs)]


def extract_chapter_sections(soup: BeautifulSoup, fallback_title: str):
    """Tách nội dung theo từng heading chương trong một EPUB document."""
    for tag in soup(['script', 'style']):
        tag.decompose()

    heading_names = {'h1', 'h2', 'h3', 'h4', 'h5'}
    sections = []
    current_title = None
    current_paragraphs = []

    for node in soup.find_all(list(heading_names) + ['p']):
        if node.name in heading_names:
            if current_title and current_paragraphs:
                sections.append((current_title, current_paragraphs))
            current_title = node.get_text(" ", strip=True) or fallback_title
            current_paragraphs = []
            continue

        if node.name == 'p':
            text = node.get_text("\n", strip=True)
            if text and current_title:
                current_paragraphs.append(text)

    if current_title and current_paragraphs:
        sections.append((current_title, current_paragraphs))

    if not sections:
        text = soup.get_text("\n", strip=True)
        return split_lines_by_chapter_titles(text.splitlines(), fallback_title)

    expanded_sections = []
    for title, paragraphs in sections:
        expanded_sections.extend(split_embedded_chapters(title, paragraphs))

    return expanded_sections


def convert_to_chapters(epub_path: str, output_dir: str):
    print(f"📖 Đang đọc file: {epub_path}")
    try:
        book = epub.read_epub(epub_path)
    except Exception as e:
        print(f"❌ Không thể đọc file Epub: {e}")
        return None

    # Lấy tên truyện và tác giả
    title_meta = book.get_metadata('DC', 'title')
    author_meta = book.get_metadata('DC', 'creator')
    title = title_meta[0][0] if title_meta else "Truyen_Khong_Ten"
    author = author_meta[0][0] if author_meta else "Chua_ro"

    print(f"🔍 Tên truyện : {title}")
    print(f"✍️  Tác giả    : {author}")
    toc_chapter_titles = collect_toc_chapter_titles(book)

    # Tạo thư mục output riêng cho từng truyện
    book_folder = os.path.join(output_dir, translated_folder_name(title))
    os.makedirs(book_folder, exist_ok=True)

    # Lưu metadata truyện vào file riêng để importer dùng sau
    with open(os.path.join(book_folder, "book_info.txt"), 'w', encoding='utf-8') as f:
        f.write(f"title={title}\n")
        f.write(f"author={author}\n")

    chapter_index = 1
    skipped = 0
    existing = 0
    created = 0
    pending_title = None
    has_seen_chapter = False
    collected_sections = []

    for item in book.get_items():
        if item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue

        soup = BeautifulSoup(item.get_body_content(), 'html.parser')
        title_only_marker = get_title_only_chapter_marker(soup)
        if title_only_marker:
            chapter_number = get_chapter_number(title_only_marker)
            if chapter_number and chapter_number in toc_chapter_titles:
                title_only_marker = toc_chapter_titles[chapter_number]
            pending_title = title_only_marker
            continue

        fallback_title = pending_title or f"Chương {chapter_index}"
        sections = extract_chapter_sections(soup, fallback_title)

        if not sections:
            skipped += 1
            continue

        for chapter_title, paragraphs in sections:
            if not has_seen_chapter and not pending_title:
                toc_title = toc_chapter_titles.get(chapter_index)
                toc_subtitle = get_chapter_subtitle(toc_title) if toc_title else ""
                if (
                    toc_title
                    and toc_subtitle
                    and not is_output_chapter_title(chapter_title)
                    and normalize_title_text(toc_subtitle) == normalize_title_text(chapter_title)
                ):
                    chapter_title = toc_title

            if pending_title:
                chapter_title, paragraphs = merge_pending_title_with_section(
                    pending_title,
                    (chapter_title, paragraphs),
                )
                pending_title = None

            if not has_seen_chapter and not is_output_chapter_title(chapter_title):
                skipped += 1
                continue

            if is_skippable_section(chapter_title, paragraphs):
                skipped += 1
                continue

            if is_output_chapter_title(chapter_title):
                has_seen_chapter = True

            collected_sections.append((chapter_title, paragraphs, chapter_index))
            chapter_index += 1

    collected_sections.sort(key=lambda section: (
        get_chapter_sort_number(section[0], section[2]),
        section[2],
    ))

    for output_index, (chapter_title, paragraphs, original_index) in enumerate(collected_sections, 1):
        file_name = f"{output_index:04d}_{sanitize_filename(chapter_title)}.md"
        file_path = os.path.join(book_folder, file_name)

        if os.path.exists(file_path):
            existing += 1
            print(f"  [skip {output_index:04d}] {chapter_title[:60]}")
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {chapter_title}\n\n")
                f.write("\n\n".join(paragraphs))
            created += 1
            print(f"  [{output_index:04d}] {chapter_title[:60]}")

    total = len(collected_sections)
    print(f"\n✅ Hoàn tất! Tổng {total} chương → thư mục: {book_folder}")
    print(f"   Tạo mới {created} file, bỏ qua {existing} file đã có.")
    print(f"   (Bỏ qua {skipped} trang phụ không phải nội dung)")
    print(f"\n📌 Bước tiếp theo:")
    print(f"   1. Nếu cần biên tập/dịch thêm, chạy translate_chapters.py trên thư mục này.")
    print(f"   2. Chạy upload_translated.py --translated-dir '{book_folder}' để upload lên Supabase\n")
    return book_folder


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
