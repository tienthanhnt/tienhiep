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
import gzip
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
    print("❌ Thiếu SUPABASE_URL hoặc SUPABASE_KEY trong file .env")
    sys.exit(1)

supabase: Client = create_client(url, key)

STORAGE_BUCKET = "covers"
CONTENT_STORAGE_BUCKET = "chapter-content"
DEFAULT_COVER = "https://images.unsplash.com/photo-1541963463532-d68292c34b19?w=300&q=80"
UPLOADABLE_DIR_SUFFIX = "_Translated"
COVER_CACHE_CONTROL = "86400"
CHAPTER_CACHE_CONTROL = "86400"
COVER_CANVAS_SIZE = "320x440"
COVER_SIZE = "240x330"
COVER_QUALITY = "46"


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def safe_storage_name(value: str) -> str:
    safe_name = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()
    return safe_name[:80] or "chapter"


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


def find_book_by_title(title: str):
    res = supabase.table("books").select("id, title, chapter_count").eq("title", title).execute()
    return res.data[0] if res.data else None


def find_book_by_id(book_id: int):
    res = supabase.table("books").select("id, title, chapter_count").eq("id", book_id).execute()
    return res.data[0] if res.data else None


def read_book_info(translated_dir: str) -> dict:
    """Đọc metadata từ book_info.txt trong thư mục translated."""
    book_info = {
        "title": "Chưa đặt tên",
        "author": "Chưa rõ",
        "status": "Đang ra",
        "description": "",
        "genres": "",
        "source_type": "",
        "ranking": "",
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
    return book_info


def upload_cover(translated_dir: str, book_title: str, author: str = "Chưa rõ") -> str:
    theme_path = find_cover_source(translated_dir)
    safe_stem = re.sub(r"[^a-zA-Z0-9_]", "_", book_title).lower()
    optimized_cover = None
    generated_cover = None
    upload_path = theme_path
    content_type = "image/png"
    extension = ".png"

    if theme_path:
        optimized_cover = create_optimized_cover(theme_path)
    else:
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
        return DEFAULT_COVER

    safe_name = safe_stem + extension
    try:
        with open(upload_path, "rb") as f:
            image_bytes = f.read()
        try:
            supabase.storage.from_(STORAGE_BUCKET).remove([
                safe_stem + ".png",
                safe_stem + ".jpg",
                safe_stem + ".jpeg",
                safe_stem + ".webp",
            ])
        except Exception:
            pass
        supabase.storage.from_(STORAGE_BUCKET).upload(
            safe_name, image_bytes, {"content-type": content_type, "cache-control": COVER_CACHE_CONTROL}
        )
        public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(safe_name)
        return f"{public_url}?v={hashlib.sha1(image_bytes).hexdigest()[:12]}"
    except Exception as e:
        print(f"⚠️  Lỗi upload ảnh: {e}")
        return DEFAULT_COVER
    finally:
        if optimized_cover or generated_cover:
            try:
                os.unlink(upload_path)
            except OSError:
                pass


def upload_chapter_content(book_id: int, chapter_number: int, chapter_title: str, html_content: str) -> tuple[str, str]:
    """Upload nội dung chương lên Storage. Trả về (content_path, public_url)."""
    safe_title = safe_storage_name(chapter_title)
    content_path = f"{book_id}/{chapter_number:04d}_{safe_title}.html.gz"
    try:
        try:
            supabase.storage.from_(CONTENT_STORAGE_BUCKET).remove([content_path])
        except Exception:
            pass
        compressed_html = gzip.compress(html_content.encode("utf-8"), compresslevel=9)

        supabase.storage.from_(CONTENT_STORAGE_BUCKET).upload(
            content_path,
            compressed_html,
            {
                "content-type": "application/gzip",
                "cache-control": CHAPTER_CACHE_CONTROL
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


def delete_chapters_by_book_id(book_id: int, batch_size: int = 50) -> int:
    """Xóa chapters theo batch nhỏ để tránh Postgres statement timeout."""
    total_deleted = 0

    while True:
        res = supabase.table("chapters") \
            .select("id") \
            .eq("book_id", book_id) \
            .order("id") \
            .limit(batch_size) \
            .execute()

        ids = [row["id"] for row in (res.data or []) if row.get("id") is not None]
        if not ids:
            return total_deleted

        supabase.table("chapters").delete().in_("id", ids).execute()
        total_deleted += len(ids)
        print(f"   🧹 Đã xóa {total_deleted} chương khỏi DB...")


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
    res = supabase.table("books").select("id, title, author, chapter_count, status, ranking").order("ranking", desc=False, nullsfirst=False).order("id").execute()
    books = res.data
    if not books:
        print("📭 Chưa có truyện nào trong Database.")
        return
    print(f"\n{'ID':<6} {'Rank':<6} {'Tên Truyện':<40} {'Tác Giả':<20} {'Chương':<8} {'TT'}")
    print("─" * 95)
    for b in books:
        rank = b.get("ranking") if b.get("ranking") is not None else ""
        print(f"{b['id']:<6} {rank!s:<6} {b['title']:<40} {(b['author'] or 'Chưa rõ'):<20} {(b['chapter_count'] or 0):<8} {b['status'] or ''}")
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
    delete_chapters_by_book_id(book["id"])
    # Xóa truyện
    supabase.table("books").delete().eq("id", book["id"]).execute()
    print(f"🗑️  Đã xóa truyện '{book['title']}' và toàn bộ chương.")


def cmd_delete_books_under_chapters(max_chapters: int, confirm: bool = False, skip_storage: bool = False):
    """Xóa tất cả truyện có chapter_count nhỏ hơn ngưỡng chỉ định."""
    if max_chapters < 1:
        print("❌ Ngưỡng số chương phải lớn hơn 0.")
        return

    res = supabase.table("books") \
        .select("id, title, author, chapter_count") \
        .lt("chapter_count", max_chapters) \
        .order("chapter_count") \
        .order("id") \
        .execute()
    books = res.data or []

    if not books:
        print(f"✅ Không có truyện nào dưới {max_chapters} chương.")
        return

    print(f"\n⚠️  Tìm thấy {len(books)} truyện dưới {max_chapters} chương:")
    print(f"{'ID':<6} {'Chương':<8} {'Tên Truyện':<45} {'Tác Giả'}")
    print("─" * 95)
    for book in books:
        print(
            f"{book['id']:<6} "
            f"{(book.get('chapter_count') or 0):<8} "
            f"{book['title']:<45} "
            f"{book.get('author') or 'Chưa rõ'}"
        )

    if not confirm:
        print("\n🔎 Đây mới là preview, chưa xóa gì.")
        print(f"   Muốn xóa thật, chạy: python manage_books.py delete-books-under-chapters {max_chapters} --yes")
        print(f"   Nếu Storage bị chậm/kẹt, chạy: python manage_books.py delete-books-under-chapters {max_chapters} --yes --skip-storage")
        return

    print("\n🚮 Đang xóa...")
    deleted = 0
    for book in books:
        book_id = book["id"]
        if not skip_storage:
            delete_book_content_files(book_id)
        delete_chapters_by_book_id(book_id)
        supabase.table("books").delete().eq("id", book_id).execute()
        deleted += 1
        print(f"   🗑️  [{book_id}] {book['title']} ({book.get('chapter_count') or 0} chương)")

    print(f"\n✅ Đã xóa {deleted} truyện dưới {max_chapters} chương.")
    if skip_storage:
        print("ℹ️  Đã bỏ qua bước xóa file nội dung trên Storage. Có thể dọn orphan Storage sau nếu cần.")


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
    delete_chapters_by_book_id(book["id"])
    supabase.table("books").update({"chapter_count": 0}).eq("id", book["id"]).execute()
    print(f"🗑️  Đã xóa toàn bộ chương. Thông tin truyện vẫn còn trong DB.")


def cmd_resync(translated_dir: str, force: bool = False):
    """Xóa toàn bộ chương cũ rồi upload lại từ thư mục."""
    if not os.path.isdir(translated_dir):
        print(f"❌ Không tìm thấy thư mục: {translated_dir}")
        return

    book_info = read_book_info(translated_dir)
    title = book_info["title"]
    ranking = parse_optional_int(book_info["ranking"], "ranking")
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
        delete_chapters_by_book_id(book["id"])
        update_data = {
            "chapter_count": 0,
            "author": book_info["author"],
            "status": book_info["status"],
            "description": book_info["description"],
            "genres": book_info["genres"],
            "source_type": book_info["source_type"],
        }
        if ranking is not None:
            update_data["ranking"] = ranking
        supabase.table("books").update(update_data).eq("id", book["id"]).execute()
        print(f"🗑️  Đã xóa chương cũ của '{title}'")
        book_id = book["id"]
    else:
        # Tạo mới
        cover_url = upload_cover(translated_dir, title, book_info["author"])
        insert_data = {
            "title": title,
            "author": book_info["author"],
            "status": book_info["status"],
            "description": book_info["description"],
            "genres": book_info["genres"],
            "source_type": book_info["source_type"],
            "rating": 8.0,
            "chapter_count": 0, "cover_url": cover_url
        }
        if ranking is not None:
            insert_data["ranking"] = ranking
        res = supabase.table("books").insert(insert_data).execute()
        book_id = res.data[0]["id"]
        print(f"✅ Đã tạo truyện mới (ID={book_id})")

    # Upload lại
    cover_url = upload_cover(translated_dir, title, book_info["author"])
    update_data = {
        "cover_url": cover_url,
        "author": book_info["author"],
        "status": book_info["status"],
        "description": book_info["description"],
        "genres": book_info["genres"],
        "source_type": book_info["source_type"],
    }
    if ranking is not None:
        update_data["ranking"] = ranking
    supabase.table("books").update(update_data).eq("id", book_id).execute()

    total = upload_all_chapters(book_id, translated_dir)
    print(f"🎉 Resync hoàn tất: {total} chương đã được upload lại.")


def cmd_resync_all(scan_dir: str = "chapters", force: bool = False):
    """Resync tất cả thư mục *_Translated trong scan_dir."""
    translated_dirs = sorted([
        os.path.join(scan_dir, d)
        for d in os.listdir(scan_dir)
        if os.path.isdir(os.path.join(scan_dir, d)) and d.endswith(UPLOADABLE_DIR_SUFFIX)
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

    # delete-books-under-chapters
    p_del_under = subparsers.add_parser(
        "delete-books-under-chapters",
        help="Xóa tất cả truyện có số chương nhỏ hơn ngưỡng"
    )
    p_del_under.add_argument("max_chapters", type=int, help="Ngưỡng số chương, ví dụ 100")
    p_del_under.add_argument("--yes", action="store_true", help="Xóa thật, bỏ qua preview")
    p_del_under.add_argument("--skip-storage", action="store_true", help="Chỉ xóa DB, bỏ qua file chapter-content trên Storage")

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
    elif args.command == "delete-books-under-chapters":
        cmd_delete_books_under_chapters(args.max_chapters, confirm=args.yes, skip_storage=args.skip_storage)
    elif args.command == "delete-chapters":
        cmd_delete_chapters(args.title, confirm=args.yes)
    elif args.command == "resync":
        cmd_resync(args.translated_dir, force=args.yes)
    elif args.command == "resync-all":
        cmd_resync_all(args.scan_dir, force=args.yes)
