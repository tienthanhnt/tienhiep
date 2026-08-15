import argparse
import os
import re
import sys
import unicodedata
from pathlib import Path


CHAPTER_RE = re.compile(r"^\s*Chương\s+(\d+)\b[:.\-\s]*(.*)$")
BODY_DUPLICATE_TITLE_RE = re.compile(r"^\s*CHƯƠNG\s+\d+\b[:.\-\s]*(.*)$")
RANGE_FILE_RE = re.compile(r"_(\d+)-(\d+)\.txt$", re.IGNORECASE)
SKIP_FILES = {"gioithieu.txt", "missing_chapters.txt"}


def remove_viet_diacritics(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def sanitize_filename(name: str) -> str:
    name = remove_viet_diacritics(name)
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.strip().replace(" ", "_")
    name = re.sub(r"[^\w\-_.]", "", name)
    return name[:80] or "chapter"


def translated_folder_name(title: str) -> str:
    folder_name = sanitize_filename(title)
    if folder_name.lower().endswith("_translated"):
        return folder_name
    return f"{folder_name}_Translated"


def natural_sort_key(path: Path):
    range_match = RANGE_FILE_RE.search(path.name)
    if range_match:
        return int(range_match.group(1))
    return 10**9


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1258"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_intro(source_dir: Path) -> dict:
    info = {
        "title": source_dir.name,
        "author": "Chưa rõ",
        "genres": "",
        "status": "Đang ra",
        "description": "",
    }
    intro_path = source_dir / "gioithieu.txt"
    if not intro_path.exists():
        return info

    lines = [line.strip() for line in read_text(intro_path).splitlines()]
    description_lines = []
    in_description = False

    for line in lines:
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("tên truyện:"):
            info["title"] = line.split(":", 1)[1].strip() or info["title"]
        elif lower.startswith("tác giả:"):
            info["author"] = line.split(":", 1)[1].strip() or info["author"]
        elif lower.startswith("thể loại:"):
            info["genres"] = line.split(":", 1)[1].strip()
        elif lower.startswith("trạng thái:"):
            status = line.split(":", 1)[1].strip()
            info["status"] = "Hoàn thành" if "hoàn" in status.lower() else status or info["status"]
        elif lower.startswith("giới thiệu:"):
            in_description = True
        elif in_description:
            description_lines.append(line)

    description = collapse_whitespace(" ".join(description_lines))
    if description:
        info["description"] = description[:500]

    return info


def split_chapters(text: str):
    chapters = []
    current_number = None
    current_title = None
    current_lines = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        match = CHAPTER_RE.match(line)

        if match:
            if current_number is not None:
                chapters.append((current_number, current_title, current_lines))

            current_number = int(match.group(1))
            title_suffix = match.group(2).strip()
            current_title = f"Chương {current_number}"
            if title_suffix:
                current_title = f"{current_title}: {title_suffix}"
            current_lines = []
            continue

        if current_number is not None:
            current_lines.append(line)

    if current_number is not None:
        chapters.append((current_number, current_title, current_lines))

    return chapters


def normalize_body(lines: list[str]) -> str:
    paragraphs = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("#cdbc"):
            continue
        if BODY_DUPLICATE_TITLE_RE.match(stripped):
            continue
        paragraphs.append(stripped)

    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def convert_txt_folder(
    source_dir: Path,
    output_root: Path,
    title_override: str | None = None,
    overwrite: bool = False,
):
    if not source_dir.is_dir():
        print(f"❌ Không tìm thấy thư mục: {source_dir}")
        sys.exit(1)

    info = parse_intro(source_dir)
    if title_override:
        info["title"] = title_override

    output_dir = output_root / translated_folder_name(info["title"])
    output_dir.mkdir(parents=True, exist_ok=True)
    if overwrite:
        for old_file in output_dir.glob("*.md"):
            old_file.unlink()

    txt_files = sorted(
        [
            path for path in source_dir.iterdir()
            if path.is_file()
            and path.suffix.lower() == ".txt"
            and path.name.lower() not in SKIP_FILES
        ],
        key=natural_sort_key,
    )

    if not txt_files:
        print(f"❌ Không tìm thấy file .txt chương trong: {source_dir}")
        sys.exit(1)

    all_chapters = []
    seen_source_numbers = set()
    duplicate_source_numbers = []
    for txt_file in txt_files:
        print(f"📄 Đang đọc {txt_file.name}")
        for chapter_number, chapter_title, lines in split_chapters(read_text(txt_file)):
            if chapter_number in seen_source_numbers:
                duplicate_source_numbers.append(chapter_number)
            seen_source_numbers.add(chapter_number)
            all_chapters.append((chapter_number, chapter_title, lines))

    created = 0
    existing = 0
    empty = 0

    with (output_dir / "book_info.txt").open("w", encoding="utf-8") as file:
        file.write(f"title={info['title']}\n")
        file.write(f"author={info['author']}\n")
        file.write(f"status={info['status']}\n")
        file.write("source_type=Convert\n")
        if info["genres"]:
            file.write(f"genres={info['genres']}\n")
        if info["description"]:
            file.write(f"description={info['description']}\n")

    source_numbers_with_body = []
    for output_number, (source_number, chapter_title, lines) in enumerate(all_chapters, 1):
        body = normalize_body(lines)
        if not body:
            empty += 1
            continue
        source_numbers_with_body.append(source_number)

        file_name = f"{output_number:04d}_{sanitize_filename(chapter_title)}.md"
        output_path = output_dir / file_name
        if output_path.exists():
            existing += 1
            continue

        output_path.write_text(f"# {chapter_title}\n\n{body}\n", encoding="utf-8")
        created += 1

    chapter_numbers = sorted(set(source_numbers_with_body))
    missing = []
    if chapter_numbers:
        expected = set(range(chapter_numbers[0], chapter_numbers[-1] + 1))
        missing = sorted(expected - set(chapter_numbers))

    print(f"\n✅ Hoàn tất: {created + existing} file chương → {output_dir}")
    print(f"   Tạo mới {created} file, bỏ qua {existing} file đã có, rỗng {empty} chương.")
    if duplicate_source_numbers:
        print("   ℹ️  Có chương phụ/trùng số nguồn, đã giữ lại bằng thứ tự đọc liên tục.")
        print(f"      Số nguồn trùng: {', '.join(map(str, sorted(set(duplicate_source_numbers))[:20]))}")
    if missing:
        preview = ", ".join(map(str, missing[:20]))
        suffix = "..." if len(missing) > 20 else ""
        print(f"   ⚠️  Thiếu {len(missing)} chương: {preview}{suffix}")
    print("\n📌 Upload bằng lệnh:")
    print(f"   python upload_translated.py --translated-dir {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Tách truyện dạng nhiều file .txt thành Markdown để upload lên web."
    )
    parser.add_argument("source_dir", help="Thư mục chứa các file .txt của truyện")
    parser.add_argument(
        "output_dir",
        nargs="?",
        default="chapters",
        help="Thư mục output gốc. Mặc định: chapters",
    )
    parser.add_argument("--title", default=None, help="Ghi đè tên truyện trong book_info.txt")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Xóa các file .md cũ trong thư mục output trước khi convert lại.",
    )
    args = parser.parse_args()

    convert_txt_folder(Path(args.source_dir), Path(args.output_dir), args.title, args.overwrite)


if __name__ == "__main__":
    main()
