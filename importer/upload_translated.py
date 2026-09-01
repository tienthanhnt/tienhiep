import os
import sys
import re
import argparse
import gzip
import time
import subprocess
import tempfile
import shutil
import unicodedata
import hashlib
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
CHAPTER_INSERT_BATCH_SIZE = 200
EXISTING_CHAPTER_PAGE_SIZE = 1000
UPLOAD_RETRY_COUNT = 3
COVER_CACHE_CONTROL = "86400"
CHAPTER_CACHE_CONTROL = "86400"
COVER_CANVAS_SIZE = "320x440"
COVER_SIZE = "240x330"
COVER_QUALITY = "46"


def safe_storage_name(value: str) -> str:
    safe_name = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()
    return safe_name[:80] or "chapter"


def safe_ascii_storage_stem(value: str, fallback: str = "cover") -> str:
    normalized = unicodedata.normalize("NFD", value).replace("Đ", "D").replace("đ", "d")
    ascii_value = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    safe_name = re.sub(r"[^a-zA-Z0-9_]+", "_", ascii_value).strip("_").lower()
    return safe_name[:64] or fallback


def get_image_converter() -> str | None:
    return shutil.which("magick") or shutil.which("convert")


def find_cover_font(candidates: list[str], fallback: str) -> str:
    converter = get_image_converter()
    if converter:
        try:
            result = subprocess.run(
                [converter, "-list", "font"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            available_fonts = set(re.findall(r"^\s*Font:\s*(.+)$", result.stdout, flags=re.MULTILINE))
            for candidate in candidates:
                if candidate in available_fonts:
                    return candidate
        except Exception:
            pass

    fc_match = shutil.which("fc-match")
    if not fc_match:
        return fallback

    for candidate in candidates:
        try:
            result = subprocess.run(
                [fc_match, "-f", "%{family}", candidate],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            continue

        family = result.stdout.split(",")[0].strip()
        if family and candidate.lower().split()[0] in family.lower():
            return family

    return fallback


def find_cover_source(translated_dir: str) -> str | None:
    for filename in ("theme.webp", "theme.jpg", "theme.jpeg", "theme.png"):
        path = os.path.join(translated_dir, filename)
        if os.path.exists(path):
            return path
    return None


def wrap_cover_text(text: str, max_chars: int = 12, max_lines: int = 5) -> str:
    words = text.split()
    if not words:
        return "Chưa đặt tên"

    lines: list[str] = []
    current = ""
    for word in words:
        next_line = f"{current} {word}".strip()
        if current and len(next_line) > max_chars:
            lines.append(current)
            current = word
        else:
            current = next_line

    if current:
        lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".") + "..."

    return "\n".join(lines)


def split_long_cover_word(word: str, max_chars: int) -> list[str]:
    return [word[index:index + max_chars] for index in range(0, len(word), max_chars)]


def wrap_cover_title(text: str, max_chars: int = 12, max_lines: int = 6) -> str:
    words = text.split()
    if not words:
        return "Chưa đặt tên"

    if len(words) <= 3 and len(text) <= max_chars + 6:
        return text

    if len(words) <= 3:
        target_lines = 1
    elif len(words) <= 6:
        target_lines = 2
    elif len(words) <= 9:
        target_lines = 3
    elif len(words) <= 12:
        target_lines = 4
    else:
        target_lines = max_lines

    target_lines = min(target_lines, max_lines)
    expanded_words = []
    for word in words:
        expanded_words.extend(split_long_cover_word(word, max_chars) if len(word) > max_chars + 4 else [word])

    target_chars = max(
        max_chars,
        (sum(len(word) for word in expanded_words) + max(0, len(expanded_words) - 1) + target_lines - 1) // target_lines,
    )
    lines = []
    current = ""

    for index, word in enumerate(expanded_words):
        next_line = f"{current} {word}".strip()
        remaining_words = len(expanded_words) - index
        remaining_lines = target_lines - len(lines) - 1
        should_wrap = (
            current
            and len(next_line) > target_chars
            and len(lines) < target_lines - 1
            and remaining_words > remaining_lines
        )

        if should_wrap:
            lines.append(current)
            current = word
        else:
            current = next_line

    if current:
        lines.append(current)

    while len(lines) < target_lines:
        longest_index = max(range(len(lines)), key=lambda index: len(lines[index]))
        line_words = lines[longest_index].split()
        if len(line_words) <= 1:
            break
        split_at = max(1, len(line_words) // 2)
        lines[longest_index:longest_index + 1] = [
            " ".join(line_words[:split_at]),
            " ".join(line_words[split_at:]),
        ]

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".") + "..."

    return "\n".join(lines)


def get_cover_title_size(title_text: str) -> int:
    lines = title_text.splitlines() or [title_text]
    line_count = len(lines)
    longest_line = max(len(line) for line in lines)
    base_size_by_lines = {
        1: 28,
        2: 25,
        3: 22,
        4: 19,
        5: 17,
        6: 15,
    }
    size = base_size_by_lines.get(line_count, 15)
    if longest_line > 14:
        size -= min(5, (longest_line - 14 + 1) // 2)
    return max(13, size)


def get_cover_author_size(author_text: str) -> int:
    lines = author_text.splitlines() or [author_text]
    longest_line = max(len(line) for line in lines)
    size = 16 if len(lines) == 1 else 14
    if longest_line > 20:
        size -= min(3, (longest_line - 20 + 2) // 3)
    return max(13, size)


def clean_cover_display_title(value: str) -> str:
    value = re.sub(r"[_-]+", " ", value or "")
    value = re.sub(r"\b\d+\s+\d+\b$", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or "Chưa đặt tên"


def normalize_cover_keyword(value: str) -> str:
    value = unicodedata.normalize("NFD", value or "")
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("đ", "d").replace("Đ", "D").lower()
    return re.sub(r"[^a-z0-9]+", " ", value)


def cover_motif_args(book_title: str) -> list[str]:
    keyword = normalize_cover_keyword(book_title)

    if "dau la" in keyword:
        return [
            "-fill", "none",
            "-stroke", "#8a6a28",
            "-strokewidth", "3",
            "-draw", "circle 160,290 160,258 circle 160,290 160,236 circle 160,290 160,214",
            "-stroke", "#3b5f86",
            "-strokewidth", "2",
            "-draw", "circle 160,290 128,290 circle 160,290 192,290",
        ]

    if "ban long" in keyword or "long" in keyword:
        return [
            "-fill", "none",
            "-stroke", "#2f4d3b",
            "-strokewidth", "5",
            "-draw", "path 'M 74 318 C 112 240, 206 354, 244 260 C 258 226, 228 204, 198 220'",
            "-stroke", "#8d6f2f",
            "-strokewidth", "3",
            "-draw", "path 'M 194 220 L 220 202 M 198 220 L 228 224 M 102 288 L 82 270 M 142 306 L 128 330 M 190 292 L 214 312'",
        ]

    if "tap do" in keyword:
        return [
            "-fill", "#efe4cf",
            "-stroke", "#8a6a28",
            "-strokewidth", "2",
            "-draw", "rectangle 88,248 150,338 rectangle 136,226 198,316 rectangle 174,252 236,342",
            "-fill", "none",
            "-stroke", "#b99654",
            "-strokewidth", "1",
            "-draw", "line 104,270 134,270 line 152,248 182,248 line 190,274 220,274",
        ]

    if "the ton" in keyword or "than" in keyword:
        return [
            "-fill", "none",
            "-stroke", "#7b6a4d",
            "-strokewidth", "3",
            "-draw", "circle 160,250 160,230 path 'M 160 270 C 136 286, 126 306, 118 332 M 160 270 C 184 286, 194 306, 202 332 M 130 334 L 190 334'",
            "-stroke", "#b99654",
            "-strokewidth", "2",
            "-draw", "circle 160,286 160,214",
        ]

    if "ngu linh" in keyword or "linh" in keyword:
        return [
            "-fill", "#d8eadf",
            "-stroke", "#789b83",
            "-strokewidth", "2",
            "-draw", "circle 160,270 160,226 circle 116,310 116,288 circle 204,310 204,288",
            "-fill", "none",
            "-stroke", "#8a6a28",
            "-strokewidth", "2",
            "-draw", "path 'M 160 314 C 138 294, 142 270, 160 250 C 178 270, 182 294, 160 314'",
        ]

    if "kiem" in keyword:
        return [
            "-fill", "none",
            "-stroke", "#3f4b55",
            "-strokewidth", "4",
            "-draw", "line 160,222 160,352",
            "-stroke", "#8a6a28",
            "-strokewidth", "3",
            "-draw", "line 126,272 194,272 line 148,352 172,352",
            "-fill", "#3f4b55",
            "-draw", "polygon 160,204 148,226 172,226",
        ]

    if "su phu" in keyword or "mat tich" in keyword:
        return [
            "-fill", "none",
            "-stroke", "#8a6a28",
            "-strokewidth", "3",
            "-draw", "line 96,332 224,332 line 116,332 116,258 line 204,332 204,258 line 104,258 216,258",
            "-stroke", "#7a8d8f",
            "-strokewidth", "2",
            "-draw", "path 'M 78 232 C 110 210, 134 226, 158 212 C 186 196, 212 216, 238 204'",
        ]

    if "tran duyen" in keyword or "duyen" in keyword:
        return [
            "-fill", "none",
            "-stroke", "#a05d4d",
            "-strokewidth", "3",
            "-draw", "path 'M 78 310 C 122 252, 198 366, 242 282'",
            "-stroke", "#8a6a28",
            "-strokewidth", "2",
            "-draw", "circle 100,302 100,292 circle 220,286 220,276",
        ]

    if "cam y" in keyword or "da hanh" in keyword:
        return [
            "-fill", "#d8c99f",
            "-stroke", "none",
            "-draw", "circle 224,226 224,190",
            "-fill", "#fbf3df",
            "-draw", "circle 240,218 240,182",
            "-fill", "none",
            "-stroke", "#2f3138",
            "-strokewidth", "3",
            "-draw", "path 'M 108 350 C 136 286, 184 286, 212 350 M 132 350 L 188 350 M 160 286 L 160 350'",
        ]

    if "ngu dao" in keyword or "dao" in keyword:
        return [
            "-fill", "none",
            "-stroke", "#8a6a28",
            "-strokewidth", "4",
            "-draw", "path 'M 92 354 C 130 314, 128 276, 160 242 C 192 276, 190 314, 228 354'",
            "-stroke", "#697d68",
            "-strokewidth", "2",
            "-draw", "line 92,354 228,354 line 118,324 202,324 line 140,292 180,292",
        ]

    return [
        "-fill", "none",
        "-stroke", "#8a6a28",
        "-strokewidth", "2",
        "-draw", "path 'M 90 330 C 124 286, 138 260, 160 226 C 182 260, 196 286, 230 330 M 106 330 L 214 330'",
    ]


def create_generated_cover(book_title: str, author: str) -> tuple[str, str, str] | None:
    converter = get_image_converter()
    if not converter:
        return None

    display_title = clean_cover_display_title(book_title)
    title_text = wrap_cover_title(display_title, max_chars=12, max_lines=6)
    title_size = get_cover_title_size(title_text)
    author_text = wrap_cover_text(f"Tác giả: {author or 'Chưa rõ'}", max_chars=20, max_lines=3)
    author_size = get_cover_author_size(author_text)
    title_font = find_cover_font(
        [
            "UVN Thuphap",
            "UVN But Long",
            "VNI-Thuphap",
            "VNI-ThuPhap",
            "SVN-Black Mango",
            "SVN-Dancing Script",
            "Dancing Script",
            "Great Vibes",
            "Pacifico",
            "Brush Script MT",
            "DFKai-SB",
            "KaiTi",
            "KaiTi_GB2312",
            "STKaiti",
            "AR PL UKai CN",
            "AR PL UKai TW",
            "Noto-Serif-CJK-SC-Bold",
            "Noto-Serif-CJK-TC-Bold",
            "Noto-Serif-CJK-JP-Bold",
            "Noto Serif CJK SC",
            "Noto Serif CJK TC",
            "Source Han Serif SC",
            "Source Han Serif CN",
            "SimSun",
            "KaiTi",
            "Liberation-Serif-Bold-Italic",
            "DejaVu-Serif-Bold-Italic",
        ],
        "DejaVu-Serif-Bold-Italic",
    )
    detail_font = find_cover_font(
        [
            "DejaVu-Serif-Italic",
            "Liberation-Serif-Italic",
            "Noto-Serif-CJK-SC",
            "Noto-Serif-CJK-TC",
            "Noto Serif CJK SC",
            "Noto Serif CJK TC",
            "Noto Serif",
            "Source Han Serif SC",
            "DejaVu Serif",
        ],
        "DejaVu-Serif-Italic",
    )

    temp = tempfile.NamedTemporaryFile(suffix=".webp", delete=False)
    temp.close()
    command = [
        converter,
        "-size", COVER_CANVAS_SIZE,
        "radial-gradient:#fbf2d6-#c4a064",
        "(",
        "-size", COVER_CANVAS_SIZE,
        "xc:none",
        "-fill", "#fff7df85",
        "-draw", "ellipse 160,212 108,156 0,360",
        "-blur", "0x26",
        ")",
        "-composite",
        "-fill", "#d8bb7a30",
        "-stroke", "none",
        "-draw", "rectangle 50,320 270,408",
        "(",
        "-background", "none",
        "-fill", "#16110d",
        "-stroke", "#16110d",
        "-strokewidth", "0.35",
        "-font", title_font,
        "-pointsize", str(title_size),
        "-gravity", "center",
        "-size", "248x207",
        f"caption:{title_text}",
        ")",
        "-gravity", "center",
        "-geometry", "+0-32",
        "-composite",
        "(",
        "-background", "none",
        "-fill", "#241b12",
        "-stroke", "none",
        "-font", detail_font,
        "-pointsize", str(author_size),
        "-gravity", "center",
        "-size", "230x64",
        f"caption:{author_text}",
        ")",
        "-gravity", "center",
        "-geometry", "+0+116",
        "-composite",
        "(",
        "-background", "none",
        "-fill", "#3d2e1e",
        "-stroke", "none",
        "-font", detail_font,
        "-pointsize", "16",
        "-gravity", "center",
        "-size", "220x28",
        "caption:Tiên Hiệp Lâu",
        ")",
        "-gravity", "center",
        "-geometry", "+0-180",
        "-composite",
        "-resize", f"{COVER_SIZE}>",
        "-strip",
        "-quality", COVER_QUALITY,
        "-define", "webp:method=6",
        temp.name,
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.getsize(temp.name) <= 0:
            raise ValueError("generated cover is empty")
        return temp.name, "image/webp", ".webp"
    except Exception:
        try:
            os.unlink(temp.name)
        except OSError:
            pass
        return None


def create_optimized_cover(source_path: str) -> tuple[str, str, str] | None:
    converter = get_image_converter()
    if not converter:
        return None

    temp = tempfile.NamedTemporaryFile(suffix=".webp", delete=False)
    temp.close()
    command = [
        converter,
        source_path,
        "-auto-orient",
        "-resize",
        f"{COVER_SIZE}>",
        "-strip",
        "-quality",
        COVER_QUALITY,
        "-define",
        "webp:method=6",
        temp.name,
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.getsize(temp.name) <= 0:
            raise ValueError("optimized cover is empty")
        return temp.name, "image/webp", ".webp"
    except Exception:
        try:
            os.unlink(temp.name)
        except OSError:
            pass
        return None


def parse_optional_int(value: str, field_name: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        print(f"⚠️  {field_name} phải là số nguyên, đang bỏ qua giá trị: {value}")
        return None


def upload_cover_image(translated_dir: str, book_title: str, author: str = "Chưa rõ") -> str:
    """Upload ảnh bìa từ thư mục Translated lên Supabase Storage. Trả về public URL."""
    theme_path = find_cover_source(translated_dir)

    optimized_cover = None
    generated_cover = None
    upload_path = theme_path
    content_type = "image/png"
    extension = ".png"

    if theme_path:
        optimized_cover = create_optimized_cover(theme_path)
    else:
        print("ℹ️  Không tìm thấy theme.webp/theme.jpg/theme.jpeg/theme.png — tự tạo bìa chữ.")
        generated_cover = create_generated_cover(book_title, author)
        if generated_cover:
            local_cover_path = os.path.join(translated_dir, "theme.webp")
            shutil.copyfile(generated_cover[0], local_cover_path)
            print(f"🖼️  Đã tạo ảnh bìa local: {local_cover_path}")

    if optimized_cover:
        upload_path, content_type, extension = optimized_cover
    elif generated_cover:
        upload_path, content_type, extension = generated_cover
    elif not upload_path:
        print("⚠️  Không tạo được ảnh bìa tự động — dùng ảnh mặc định.")
        return DEFAULT_COVER

    try:
        with open(upload_path, "rb") as f:
            image_bytes = f.read()
        safe_stem = safe_ascii_storage_stem(book_title)
        content_hash = hashlib.sha1(image_bytes).hexdigest()[:12]
        safe_name = f"{safe_stem}-{content_hash}{extension}"
        supabase.storage.from_(STORAGE_BUCKET).upload(
            safe_name,
            image_bytes,
            {"content-type": content_type, "cache-control": COVER_CACHE_CONTROL, "upsert": "true"}
        )
        public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(safe_name)
        print(f"🖼️  Đã upload ảnh bìa WebP tối ưu: {public_url}")
        return public_url
    except Exception as e:
        print(f"⚠️  Lỗi upload ảnh bìa: {e}")
        print("   Gợi ý: Hãy tạo bucket 'covers' (Public) trong Supabase Storage.")
        return DEFAULT_COVER
    finally:
        if optimized_cover or generated_cover:
            try:
                os.unlink(upload_path)
            except OSError:
                pass


def upload_chapter_content(
    book_id: int,
    chapter_number: int,
    chapter_title: str,
    html_content: str,
    version_suffix: str | None = None,
) -> tuple[str, str]:
    """Upload nội dung chương lên Storage. Trả về (content_path, public_url)."""
    safe_title = safe_storage_name(chapter_title)
    suffix = f"_{version_suffix}" if version_suffix else ""
    content_path = f"{book_id}/{chapter_number:04d}_{safe_title}{suffix}.html.gz"

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
                    "cache-control": CHAPTER_CACHE_CONTROL,
                    "upsert": "true"
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
        "ranking": "",
        "book_id": "",
        "old_title": "",
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
    ranking = parse_optional_int(book_info["ranking"], "ranking")

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
        if ranking is not None:
            update_data["ranking"] = ranking
        if cover_url != DEFAULT_COVER:
            update_data["cover_url"] = cover_url
        supabase.table("books").update(update_data).eq("id", book_id).execute()
        print(f"ℹ️  Đã cập nhật metadata: {book_info['status']}")
        if cover_url != DEFAULT_COVER:
            print(f"🖼️  Đã giữ/cập nhật ảnh bìa cho truyện ID={book_id}")
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
    if ranking is not None:
        book_data["ranking"] = ranking
    res = supabase.table("books").insert(book_data).execute()
    book_id = res.data[0]['id']
    print(f"✅ Đã tạo truyện mới với ID = {book_id}")
    return book_id


def get_existing_book(title: str) -> dict | None:
    res = supabase.table("books").select("id,cover_url").eq("title", title).execute()
    return res.data[0] if res.data else None


def get_existing_chapter_numbers(book_id: int) -> set[int]:
    chapter_numbers: set[int] = set()
    start = 0

    while True:
        end = start + EXISTING_CHAPTER_PAGE_SIZE - 1
        res = (
            supabase.table("chapters")
            .select("chapter_number")
            .eq("book_id", book_id)
            .range(start, end)
            .execute()
        )
        rows = res.data or []
        chapter_numbers.update(
            int(row["chapter_number"])
            for row in rows
            if row.get("chapter_number") is not None
        )
        if len(rows) < EXISTING_CHAPTER_PAGE_SIZE:
            break
        start += EXISTING_CHAPTER_PAGE_SIZE

    return chapter_numbers


def find_chapter_file(translated_dir: str, chapter_number: int, chapter_file: str | None = None) -> str | None:
    if chapter_file:
        file_path = chapter_file
        if not os.path.isabs(file_path) and not os.path.isfile(file_path):
            file_path = os.path.join(translated_dir, file_path)
        return file_path if os.path.isfile(file_path) else None

    prefix = f"{chapter_number:04d}_"
    matches = sorted(
        filename
        for filename in os.listdir(translated_dir)
        if filename.endswith(".md") and filename.startswith(prefix)
    )
    if not matches:
        return None

    return os.path.join(translated_dir, matches[0])


def parse_chapter_markdown(file_path: str, chapter_number: int) -> tuple[str, str]:
    with open(file_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    title_match = re.search(r"^#\s+(.+)$", md_content, flags=re.MULTILINE)
    chapter_title = title_match.group(1).strip() if title_match else f"Chương {chapter_number}"
    html_content = markdown.markdown(md_content)
    return chapter_title, html_content


def remove_content_paths(paths: list[str | None]):
    removable_paths = [path for path in paths if path]
    if not removable_paths:
        return

    try:
        supabase.storage.from_(CONTENT_STORAGE_BUCKET).remove(removable_paths)
    except Exception as e:
        print(f"⚠️  Không xóa được file content cũ trên Storage: {e}")


def force_update_chapter(translated_dir: str, chapter_number: int, chapter_file: str | None = None):
    print(f"🔁 Force update chương {chapter_number} từ: {translated_dir}")

    if not os.path.isdir(translated_dir):
        print(f"❌ Không tìm thấy thư mục: {translated_dir}")
        return

    if chapter_number <= 0:
        print("❌ Số chương phải lớn hơn 0.")
        return

    file_path = find_chapter_file(translated_dir, chapter_number, chapter_file)
    if not file_path:
        print(f"❌ Không tìm thấy file .md cho chương {chapter_number}.")
        print(f"   Mặc định tool tìm file bắt đầu bằng: {chapter_number:04d}_")
        print("   Nếu muốn dùng file khác, truyền thêm --force-chapter-file <file.md>")
        return

    validate_content_storage_setup()
    book_info = read_book_info(translated_dir)
    existing_book = get_existing_book(book_info["title"])
    if not existing_book:
        print(f"❌ Truyện '{book_info['title']}' chưa có trên DB. Hãy upload truyện trước khi force update chương.")
        return

    book_id = existing_book["id"]
    chapter_title, html_content = parse_chapter_markdown(file_path, chapter_number)
    content_hash = hashlib.sha1(html_content.encode("utf-8")).hexdigest()[:10]
    version_suffix = f"v{content_hash}"

    res = (
        supabase.table("chapters")
        .select("id, content_path")
        .eq("book_id", book_id)
        .eq("chapter_number", chapter_number)
        .execute()
    )
    old_chapters = res.data or []

    content_path, content_url = upload_chapter_content(
        book_id,
        chapter_number,
        chapter_title,
        html_content,
        version_suffix=version_suffix,
    )

    if old_chapters:
        chapter_id = old_chapters[0]["id"]
        supabase.table("chapters").update({
            "title": chapter_title,
            "content_html": "",
            "content_path": content_path,
            "content_url": content_url,
        }).eq("id", chapter_id).execute()

        duplicate_ids = [row["id"] for row in old_chapters[1:] if row.get("id")]
        if duplicate_ids:
            supabase.table("chapters").delete().in_("id", duplicate_ids).execute()
        remove_content_paths([row.get("content_path") for row in old_chapters if row.get("content_path") != content_path])
        print(f"✅ Đã update chương {chapter_number}: {chapter_title}")
    else:
        supabase.table("chapters").insert({
            "book_id": book_id,
            "title": chapter_title,
            "content_html": "",
            "content_path": content_path,
            "content_url": content_url,
            "chapter_number": chapter_number,
        }).execute()
        print(f"✅ Đã insert lại chương {chapter_number}: {chapter_title}")

    count_res = supabase.table("chapters").select("id", count="exact").eq("book_id", book_id).execute()
    supabase.table("books").update({"chapter_count": count_res.count}).eq("id", book_id).execute()
    print(f"   File local : {file_path}")
    print(f"   Storage    : {content_path}")
    print(f"   Tổng chương: {count_res.count}")


def refresh_cover_only(translated_dir: str):
    if not os.path.isdir(translated_dir):
        print(f"❌ Không tìm thấy thư mục: {translated_dir}")
        return

    book_info = read_book_info(translated_dir)
    title = book_info["title"]
    res = supabase.table("books").select("id,title").eq("title", title).execute()
    if not res.data:
        print(f"[-] Bỏ qua '{title}': chưa có trên Database.")
        return

    cover_url = upload_cover_image(translated_dir, title, book_info["author"])
    if cover_url == DEFAULT_COVER:
        print(f"[-] Bỏ qua '{title}': không có ảnh bìa hợp lệ và không tự tạo được.")
        return

    book_id = res.data[0]["id"]
    supabase.table("books").update({"cover_url": cover_url}).eq("id", book_id).execute()
    print(f"✅ Đã cập nhật bìa tối ưu cho '{title}' (ID={book_id})")


def find_existing_book_for_info(book_info: dict) -> dict | None:
    book_id = parse_optional_int(book_info.get("book_id", ""), "book_id")
    if book_id is not None:
        res = supabase.table("books").select("id,title").eq("id", book_id).execute()
        if res.data:
            return res.data[0]
        print(f"[-] Không tìm thấy truyện có book_id={book_id}.")
        return None

    lookup_title = book_info.get("old_title") or book_info["title"]
    res = supabase.table("books").select("id,title").eq("title", lookup_title).execute()
    if res.data:
        return res.data[0]

    print(f"[-] Không tìm thấy truyện '{lookup_title}' trên Database.")
    if book_info.get("old_title"):
        print(f"   title mới trong book_info.txt đang là: {book_info['title']}")
    else:
        print("   Nếu bạn đang đổi title, hãy thêm old_title=<tên hiện tại trên web> hoặc book_id=<id truyện> vào book_info.txt.")
    return None


def refresh_info_only(translated_dir: str):
    if not os.path.isdir(translated_dir):
        print(f"❌ Không tìm thấy thư mục: {translated_dir}")
        return

    info_path = os.path.join(translated_dir, "book_info.txt")
    if not os.path.exists(info_path):
        print(f"[-] Bỏ qua '{translated_dir}': không tìm thấy book_info.txt.")
        return

    book_info = read_book_info(translated_dir)
    book = find_existing_book_for_info(book_info)
    if not book:
        return

    ranking = parse_optional_int(book_info["ranking"], "ranking")
    update_data = {
        "title": book_info["title"],
        "author": book_info["author"],
        "status": book_info["status"],
        "description": book_info["description"],
        "genres": book_info["genres"],
        "source_type": book_info["source_type"],
    }
    if ranking is not None:
        update_data["ranking"] = ranking

    supabase.table("books").update(update_data).eq("id", book["id"]).execute()
    old_title = book.get("title") or book_info["title"]
    print(f"✅ Đã cập nhật book_info cho '{old_title}' → '{book_info['title']}' (ID={book['id']})")


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

    existing_book = get_existing_book(book_info["title"])
    if existing_book:
        cover_url = existing_book.get("cover_url") or DEFAULT_COVER
        print("🖼️  Truyện đã có trên DB — bỏ qua upload lại ảnh bìa. Dùng --covers-only nếu muốn cập nhật bìa.")
    else:
        cover_url = upload_cover_image(translated_dir, book_info["title"], book_info["author"])
    book_id = get_or_create_book(book_info, cover_url)
    existing_chapter_numbers = get_existing_chapter_numbers(book_id)
    if existing_chapter_numbers:
        print(f"🔎 Đã tải danh sách {len(existing_chapter_numbers)} chương hiện có để bỏ qua nhanh.")

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

        if chapter_number in existing_chapter_numbers:
            print(f"[-] Bỏ qua Chương {chapter_number}: Đã có trên Database.")
            continue
        
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
        existing_chapter_numbers.add(chapter_number)

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
    parser.add_argument(
        '--covers-only',
        action='store_true',
        help='Chỉ tối ưu/upload lại ảnh bìa và cập nhật cover_url, không xử lý chương.'
    )
    parser.add_argument(
        '--info-only',
        action='store_true',
        help='Chỉ đồng bộ book_info.txt vào bảng books, không xử lý chương và không upload ảnh bìa.'
    )
    parser.add_argument(
        '--force-chapter',
        type=int,
        default=None,
        help='Update lại đúng một chương theo số chương, kể cả khi chương đã tồn tại trong DB.'
    )
    parser.add_argument(
        '--force-chapter-file',
        default=None,
        help='File .md cụ thể để dùng với --force-chapter. Mặc định tìm file bắt đầu bằng số chương, ví dụ 0267_.'
    )
    args = parser.parse_args()

    exclusive_modes = [args.covers_only, args.info_only, args.force_chapter is not None]
    if sum(1 for enabled in exclusive_modes if enabled) > 1:
        print("❌ Chỉ dùng một trong các option: --covers-only, --info-only hoặc --force-chapter.")
        sys.exit(1)

    if args.force_chapter is not None and not args.translated_dir:
        print("❌ --force-chapter cần đi kèm --translated-dir để tránh update nhầm truyện.")
        sys.exit(1)

    if args.translated_dir:
        # Upload 1 truyện cụ thể
        if args.covers_only:
            refresh_cover_only(args.translated_dir)
        elif args.info_only:
            refresh_info_only(args.translated_dir)
        elif args.force_chapter is not None:
            force_update_chapter(
                args.translated_dir,
                args.force_chapter,
                chapter_file=args.force_chapter_file,
            )
        else:
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
            if args.covers_only:
                refresh_cover_only(d)
            elif args.info_only:
                refresh_info_only(d)
            else:
                upload_chapters(d, limit=args.limit)

        print(f"\n{'='*60}")
        print(f"🏆 Đã xử lý xong tất cả {len(translated_dirs)} bộ truyện!")
