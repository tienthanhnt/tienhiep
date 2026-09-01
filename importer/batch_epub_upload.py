"""
Batch convert many EPUB files, for example 50 books, to Markdown folders,
enrich book_info.txt, then upload.

Usage:
  python batch_epub_upload.py /path/to/epub_folder
  python batch_epub_upload.py /path/to/epub_folder --convert-only
  python batch_epub_upload.py /path/to/epub_folder --output-dir chapters
"""

import argparse
import json
import random
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import epub_to_md


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "chapters"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OLLAMA_MODEL = "qwen3:14b"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
BATCH_MARKER_FILE = ".batch_epub_upload.json"
BATCH_MANIFEST_FILE = ".batch_epub_upload_latest.json"
DEFAULT_KEYWORDS = [
    "Tiên Hiệp",
    "Tu Tiên",
    "Huyền Huyễn",
    "Kiếm Hiệp",
    "Truyện Dịch",
    "Truyện Full",
    "Hoàn Thành",
    "Đọc Truyện Online",
]
BLOCKED_KEYWORD_PARTS = [
    "đam mỹ",
    "dam my",
    "ngôn tình",
    "ngon tinh",
    "manhua",
    "manga",
    "võng du",
    "vong du",
    "đô thị",
    "do thi",
    "xuyên không",
    "xuyen khong",
    "hệ thống",
    "he thong",
]


def clean_text(value: str, fallback: str = "") -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    return value or fallback


def read_book_info(book_dir: Path) -> dict[str, str]:
    info = {
        "title": book_dir.name.removesuffix("_Translated").replace("_", " "),
        "author": "Chưa rõ",
    }
    info_path = book_dir / "book_info.txt"
    if not info_path.exists():
        return info

    for line in info_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in info:
            info[key] = clean_text(value, info[key])

    return info


def build_seo_keywords(title: str, author: str) -> list[str]:
    keywords = []
    for value in [title, author, *DEFAULT_KEYWORDS]:
        value = clean_text(value)
        if not value or value.lower() in {"chưa rõ", "chua ro"}:
            continue
        if value not in keywords:
            keywords.append(value)
        if len(keywords) == 8:
            break

    for value in DEFAULT_KEYWORDS:
        if len(keywords) == 8:
            break
        if value not in keywords:
            keywords.append(value)

    return keywords[:8]


def build_seo_description(title: str, author: str, keywords: list[str]) -> str:
    keyword_text = ", ".join(keywords[:5])
    author_text = author if author and author != "Chưa rõ" else "tác giả đang cập nhật"
    return (
        f"Đọc truyện {title} của {author_text} bản dịch hoàn thành tại Tiên Hiệp Lâu. "
        f"Nội dung được trình bày dễ đọc trên điện thoại và máy tính, phù hợp độc giả yêu thích {keyword_text}."
    )


def build_ollama_prompt(title: str, author: str) -> str:
    return f"""Bạn là biên tập viên SEO cho website đọc truyện tiên hiệp Tiên Hiệp Lâu.

Hãy viết metadata SEO bằng tiếng Việt cho truyện:
- Tên truyện: {title}
- Tác giả: {author}

Yêu cầu description:
- Dài khoảng 180-250 chữ.
- Văn phong tự nhiên, hấp dẫn, hợp trang đọc truyện online.
- Có nhắc tên truyện và tác giả.
- Nên có các cụm từ SEO tự nhiên như: đọc truyện, truyện tiên hiệp, truyện dịch, truyện full, tu tiên, huyền huyễn.
- Không bịa chi tiết quá cụ thể nếu không chắc.
- Không dùng tiếng Trung, tiếng Anh, pinyin, ký tự lạ.

Yêu cầu keywords:
- Tạo đúng 8 keyword/tag SEO.
- Mỗi keyword dài 2-5 từ.
- Keyword phải là tiếng Việt có dấu.
- Ưu tiên keyword người đọc thật sự có thể tìm kiếm.
- Không dùng tag sai thể loại như: đam mỹ, ngôn tình, manhua, manga, võng du, đô thị, xuyên không, hệ thống.
- Không dùng ký tự lạ, không dùng tiếng Trung, không dùng pinyin.
- Không lặp keyword gần giống nhau quá nhiều.

Chỉ trả lời đúng format sau, không giải thích thêm:

Description: ...
Keywords: keyword 1, keyword 2, keyword 3, keyword 4, keyword 5, keyword 6, keyword 7, keyword 8
"""


def contains_cjk(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value))


def normalize_keyword(keyword: str) -> str:
    keyword = clean_text(keyword)
    keyword = keyword.strip(" ,.;:-\"'")
    return keyword


def validate_ai_metadata(description: str, keywords: list[str]) -> bool:
    if len(description.split()) < 120:
        return False
    if contains_cjk(description):
        return False
    if len(keywords) != 8:
        return False

    seen = set()
    for keyword in keywords:
        normalized = normalize_keyword(keyword)
        lowered = normalized.lower()
        if not normalized or contains_cjk(normalized):
            return False
        if lowered in seen:
            return False
        if len(normalized.split()) < 2 or len(normalized.split()) > 5:
            return False
        if any(blocked in lowered for blocked in BLOCKED_KEYWORD_PARTS):
            return False
        seen.add(lowered)

    return True


def parse_ai_metadata(output: str) -> tuple[str, list[str]] | None:
    description_match = re.search(
        r"Description:\s*(.+?)(?:\n\s*Keywords:|$)",
        output,
        flags=re.IGNORECASE | re.DOTALL,
    )
    keywords_match = re.search(r"Keywords:\s*(.+)$", output, flags=re.IGNORECASE | re.DOTALL)
    if not description_match or not keywords_match:
        return None

    description = clean_text(description_match.group(1).strip().strip("\""))
    raw_keywords = keywords_match.group(1).replace("\n", ",")
    keywords = [normalize_keyword(part) for part in raw_keywords.split(",")]
    keywords = [keyword for keyword in keywords if keyword]

    if not validate_ai_metadata(description, keywords):
        return None

    return description, keywords


def generate_ai_metadata(
    title: str,
    author: str,
    model: str,
    ollama_url: str,
    timeout: int,
) -> tuple[str, list[str]] | None:
    payload = {
        "model": model,
        "prompt": build_ollama_prompt(title, author),
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.25,
            "num_predict": 700,
        },
    }

    req = urllib.request.Request(
        ollama_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"⚠️  Ollama lỗi, dùng SEO template fallback: {exc}")
        return None

    parsed = parse_ai_metadata(data.get("response", ""))
    if not parsed:
        print("⚠️  Ollama trả metadata không đạt format/chất lượng, dùng SEO template fallback.")
        return None

    return parsed


def write_auto_book_info(
    book_dir: Path,
    ranking: int,
    use_ai_seo: bool,
    ollama_model: str,
    ollama_url: str,
    ollama_timeout: int,
):
    info = read_book_info(book_dir)
    title = clean_text(info.get("title", ""), "Truyện Không Tên")
    author = clean_text(info.get("author", ""), "Chưa rõ")
    metadata = None

    if use_ai_seo:
        print(f"🤖 Đang tạo SEO bằng Ollama model {ollama_model}...")
        metadata = generate_ai_metadata(title, author, ollama_model, ollama_url, ollama_timeout)

    if metadata:
        description, keywords = metadata
        print("✅ Đã tạo SEO bằng AI.")
    else:
        keywords = build_seo_keywords(title, author)
        description = build_seo_description(title, author, keywords)

    lines = [
        f"title={title}",
        f"author={author}",
        "status=Hoàn thành",
        "source_type=Dịch",
        f"ranking={ranking}",
        f"genres={', '.join(keywords)}",
        f"description={description}",
    ]
    (book_dir / "book_info.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_epub_output_dir(epub_path: Path, output_dir: Path) -> Path | None:
    try:
        book = epub_to_md.read_epub_resilient(str(epub_path))
    except Exception as exc:
        print(f"❌ Không đọc được metadata EPUB để xác định folder output: {epub_path.name}: {exc}")
        return None

    title_meta = book.get_metadata("DC", "title")
    title = title_meta[0][0] if title_meta else "Truyen_Khong_Ten"
    return output_dir / epub_to_md.translated_folder_name(title)


def write_batch_marker(
    book_dir: Path,
    batch_id: str,
    epub_path: Path,
    ranking: int,
    use_ai_seo: bool,
    ollama_model: str,
):
    marker = {
        "tool": "batch_epub_upload.py",
        "batch_id": batch_id,
        "source_epub": str(epub_path),
        "ranking": ranking,
        "ai_seo": use_ai_seo,
        "ollama_model": ollama_model if use_ai_seo else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (book_dir / BATCH_MARKER_FILE).write_text(
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_batch_manifest(output_dir: Path, batch_id: str, book_dirs: list[Path]):
    manifest = {
        "tool": "batch_epub_upload.py",
        "batch_id": batch_id,
        "book_dirs": [str(path) for path in book_dirs],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / BATCH_MANIFEST_FILE).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_latest_batch_manifest(output_dir: Path) -> list[Path]:
    manifest_path = output_dir / BATCH_MANIFEST_FILE
    if not manifest_path.exists():
        return []

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"⚠️  Không đọc được manifest batch mới nhất: {exc}")
        return []

    book_dirs = []
    for raw_path in manifest.get("book_dirs", []):
        path = Path(raw_path).expanduser().resolve()
        marker_path = path / BATCH_MARKER_FILE
        if path.is_dir() and marker_path.exists():
            book_dirs.append(path)

    return book_dirs


def list_epub_files(epub_dir: Path) -> list[Path]:
    return sorted(
        [path for path in epub_dir.iterdir() if path.is_file() and path.suffix.lower() == ".epub"],
        key=lambda path: path.name.lower(),
    )


def convert_epub(
    epub_path: Path,
    output_dir: Path,
    ranking: int,
    use_ai_seo: bool,
    ollama_model: str,
    ollama_url: str,
    ollama_timeout: int,
    batch_id: str,
) -> Path | None:
    book_dir = epub_to_md.convert_to_chapters(str(epub_path), str(output_dir))
    if not book_dir:
        return None

    book_dir_path = Path(book_dir)
    write_auto_book_info(
        book_dir_path,
        ranking,
        use_ai_seo,
        ollama_model,
        ollama_url,
        ollama_timeout,
    )
    write_batch_marker(book_dir_path, batch_id, epub_path, ranking, use_ai_seo, ollama_model)
    print(f"📝 Đã ghi book_info SEO: {book_dir_path / 'book_info.txt'}")
    return book_dir_path


def upload_book(book_dir: Path):
    try:
        from dotenv import load_dotenv

        load_dotenv(SCRIPT_DIR / ".env")
    except Exception:
        pass

    import upload_translated

    upload_translated.upload_chapters(str(book_dir))


def main():
    parser = argparse.ArgumentParser(
        description="Tự động convert folder nhiều EPUB, ghi SEO book_info.txt và upload lên web."
    )
    parser.add_argument(
        "epub_dir",
        nargs="?",
        help="Folder chứa các file .epub cần upload. Không cần truyền khi dùng --upload-only.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Folder output chứa các *_Translated. Mặc định: importer/chapters",
    )
    parser.add_argument(
        "--convert-only",
        action="store_true",
        help="Chỉ convert và ghi book_info.txt, chưa upload lên Supabase.",
    )
    parser.add_argument(
        "--upload-only",
        action="store_true",
        help="Bỏ qua convert, chỉ upload các folder trong manifest batch mới nhất.",
    )
    parser.add_argument(
        "--upload-limit",
        type=int,
        default=None,
        help="Chỉ upload tối đa N truyện từ manifest batch mới nhất.",
    )
    parser.add_argument(
        "--upload-skip",
        type=int,
        default=0,
        help="Bỏ qua N truyện đầu trong manifest khi dùng --upload-only.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed random ranking để lần chạy sau sinh ranking giống nhau nếu cần.",
    )
    parser.add_argument(
        "--ollama-model",
        default=DEFAULT_OLLAMA_MODEL,
        help=f"Model Ollama dùng để viết SEO. Mặc định: {DEFAULT_OLLAMA_MODEL}",
    )
    parser.add_argument(
        "--ollama-url",
        default=DEFAULT_OLLAMA_URL,
        help=f"Endpoint Ollama generate API. Mặc định: {DEFAULT_OLLAMA_URL}",
    )
    parser.add_argument(
        "--ollama-timeout",
        type=int,
        default=300,
        help="Timeout mỗi lần gọi Ollama, tính bằng giây. Mặc định: 300",
    )
    parser.add_argument(
        "--no-ai-seo",
        action="store_true",
        help="Không gọi Ollama, dùng template SEO cũ.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Cho phép convert lại nếu folder output của truyện đã tồn tại.",
    )
    args = parser.parse_args()

    if args.convert_only and args.upload_only:
        print("❌ Chỉ dùng một trong hai option: --convert-only hoặc --upload-only.")
        sys.exit(1)
    if args.upload_limit is not None and args.upload_limit < 1:
        print("❌ --upload-limit phải lớn hơn 0.")
        sys.exit(1)
    if args.upload_skip < 0:
        print("❌ --upload-skip không được âm.")
        sys.exit(1)

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.seed is not None:
        random.seed(args.seed)

    if args.upload_only:
        book_dirs = read_latest_batch_manifest(output_dir)
        if not book_dirs:
            print(f"⚠️  Không tìm thấy manifest batch mới nhất trong: {output_dir}")
            print("   Hãy chạy convert bằng batch_epub_upload.py trước, hoặc bỏ --upload-only để convert batch mới.")
            return
        total_in_manifest = len(book_dirs)
        if args.upload_skip:
            book_dirs = book_dirs[args.upload_skip:]
        if args.upload_limit is not None:
            book_dirs = book_dirs[:args.upload_limit]
        if not book_dirs:
            print(f"⚠️  Không còn truyện nào để upload sau --upload-skip trong batch {total_in_manifest} truyện.")
            return

        print(
            f"📌 Upload-only: chỉ upload {len(book_dirs)}/{total_in_manifest} "
            "folder trong batch mới nhất."
        )
        print("📚 Danh sách sẽ upload:")
        for index, book_dir in enumerate(book_dirs, 1):
            print(f"   {index}. {book_dir.name}")
    else:
        if not args.epub_dir:
            print("❌ Thiếu folder EPUB.")
            print("   Ví dụ: python batch_epub_upload.py /home/thanh/Downloads/epub_batch")
            sys.exit(1)

        epub_dir = Path(args.epub_dir).expanduser().resolve()
        if not epub_dir.is_dir():
            print(f"❌ Không tìm thấy folder EPUB: {epub_dir}")
            sys.exit(1)

        epub_files = list_epub_files(epub_dir)
        if not epub_files:
            print(f"⚠️  Không tìm thấy file .epub nào trong: {epub_dir}")
            return

        print(f"📚 Tìm thấy {len(epub_files)} file EPUB.")
        batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        book_dirs = []
        for index, epub_path in enumerate(epub_files, 1):
            expected_book_dir = get_epub_output_dir(epub_path, output_dir)
            if expected_book_dir and expected_book_dir.exists() and not args.overwrite_existing:
                print(f"\n{'=' * 70}")
                print(f"⏭️  [{index}/{len(epub_files)}] Bỏ qua vì folder đã tồn tại: {expected_book_dir}")
                print("   Nếu muốn convert lại folder này, chạy thêm --overwrite-existing.")
                continue

            ranking = random.randint(50, 100)
            print(f"\n{'=' * 70}")
            print(f"📖 [{index}/{len(epub_files)}] Convert: {epub_path.name} | ranking={ranking}")
            book_dir = convert_epub(
                epub_path,
                output_dir,
                ranking,
                not args.no_ai_seo,
                args.ollama_model,
                args.ollama_url,
                args.ollama_timeout,
                batch_id,
            )
            if book_dir:
                book_dirs.append(book_dir)

        write_batch_manifest(output_dir, batch_id, book_dirs)
        print(f"\n📌 Đã ghi manifest batch mới nhất: {output_dir / BATCH_MANIFEST_FILE}")

    if args.convert_only:
        print(f"\n✅ Convert xong {len(book_dirs)} truyện. Chưa upload vì đang dùng --convert-only.")
        return

    print(f"\n🚀 Bắt đầu upload {len(book_dirs)} truyện lên web...")
    for index, book_dir in enumerate(book_dirs, 1):
        print(f"\n{'=' * 70}")
        print(f"⬆️  [{index}/{len(book_dirs)}] Upload: {book_dir}")
        upload_book(book_dir)

    print(f"\n🏆 Hoàn tất batch: {len(book_dirs)} truyện.")


if __name__ == "__main__":
    main()
