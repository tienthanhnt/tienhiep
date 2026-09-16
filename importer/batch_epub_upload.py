"""
Batch convert many EPUB files, for example 50 books, to Markdown folders,
enrich book_info.txt, then upload new books to Cloudflare D1 + R2.

Usage:
  python batch_epub_upload.py /path/to/epub_folder --convert-only
  python batch_epub_upload.py --upload-only --upload-limit 3
  python batch_epub_upload.py /path/to/epub_folder --convert-only
  python batch_epub_upload.py --upload-only
"""

import argparse
import contextlib
import io
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import epub_to_md
from supabase_lookup import fetch_supabase_title_slugs, slugify


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "chapters"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OLLAMA_MODEL = "qwen3:14b"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_GROK_MODEL = "grok-3-mini"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
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
        if len(keywords) == 6:
            break

    for value in DEFAULT_KEYWORDS:
        if len(keywords) == 6:
            break
        if value not in keywords:
            keywords.append(value)

    return keywords[:6]


def build_seo_description(title: str, author: str, keywords: list[str]) -> str:
    keyword_text = ", ".join(keywords[:5])
    author_text = author if author and author != "Chưa rõ" else "tác giả đang cập nhật"
    return (
        f"Đọc truyện {title} của {author_text} bản dịch hoàn thành tại Tiên Hiệp Lâu. "
        f"Nội dung được trình bày dễ đọc trên điện thoại và máy tính, phù hợp độc giả yêu thích {keyword_text}."
    )


def clean_title_for_seo(title: str) -> str:
    title = re.sub(r"^\s*\([^)]*\d{4}[^)]*\)\s*", "", title)
    title = re.sub(r"\s*\((?:dịch|convert|converted)\)\s*$", "", title, flags=re.IGNORECASE)
    return clean_text(title)


def list_chapter_paths(book_dir: Path) -> list[Path]:
    def chapter_number(path: Path) -> tuple[int, str]:
        match = re.match(r"(\d+)", path.name)
        return (int(match.group(1)) if match else sys.maxsize, path.name)

    return sorted(book_dir.glob("*.md"), key=chapter_number)


def read_story_context(book_dir: Path, max_files: int = 2, max_chars: int = 3000) -> str:
    excerpts = []
    remaining = max_chars
    for chapter_path in list_chapter_paths(book_dir)[:max_files]:
        text = chapter_path.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"^#{1,6}\s+.*$", "", text, flags=re.MULTILINE)
        text = clean_text(text)
        if not text:
            continue
        excerpt = text[:remaining]
        excerpts.append(excerpt)
        remaining -= len(excerpt)
        if remaining <= 0:
            break
    return "\n\n".join(excerpts)


def read_ending_context(book_dir: Path, max_chars: int = 1500) -> str:
    chapter_paths = list_chapter_paths(book_dir)
    if not chapter_paths:
        return ""
    text = chapter_paths[-1].read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"^#{1,6}\s+.*$", "", text, flags=re.MULTILINE)
    return clean_text(text)[-max_chars:]


def build_ollama_prompt(
    title: str,
    author: str,
    story_context: str,
    ending_context: str,
    chapter_count: int,
) -> str:
    return f"""Bạn là biên tập viên SEO cho website đọc truyện tiên hiệp Tiên Hiệp Lâu.

Hãy viết metadata SEO bằng tiếng Việt cho truyện:
- Tên truyện: {title}
- Tác giả: {author}

Nội dung mẫu lấy trực tiếp từ truyện:
---
{story_context}
---

Thông tin dùng để đánh giá trạng thái:
- Tổng số chương đã convert: {chapter_count}
- Đoạn cuối của chương cuối:
---
{ending_context}
---

Yêu cầu description:
- Dài khoảng 100-140 từ, tối thiểu 80 từ.
- Văn phong tự nhiên, hấp dẫn, hợp trang đọc truyện online.
- Có nhắc tên truyện và tác giả.
- Nên có các cụm từ SEO tự nhiên như: đọc truyện, truyện tiên hiệp, truyện dịch, truyện full, tu tiên, huyền huyễn.
- Không bịa chi tiết quá cụ thể nếu không chắc.
- Chỉ mô tả nhân vật, bối cảnh và tình tiết xuất hiện trong nội dung mẫu.
- Không khẳng định "dịch chuẩn", "đầy đủ", "không gián đoạn" hoặc chất lượng bản dịch.
- Không dùng các câu quảng cáo sáo rỗng như "mọi giấc mơ trở thành hiện thực".
- Không dùng tiếng Trung, tiếng Anh, pinyin, ký tự lạ.

Yêu cầu keywords:
- Tạo đúng 6 keyword/tag SEO.
- Mỗi keyword đúng 2 từ.
- Ví dụ hợp lệ: "tiên hiệp", "tu tiên", "truyện dịch", "truyện full", "đọc truyện", "huyền huyễn".
- Ví dụ không hợp lệ vì có 3 từ: "truyện tiên hiệp", "đọc truyện online", "tu tiên huyền huyễn".
- Keyword phải là tiếng Việt có dấu.
- Ưu tiên keyword người đọc thật sự có thể tìm kiếm.
- Không dùng tag sai thể loại như: đam mỹ, ngôn tình, manhua, manga, võng du, đô thị, xuyên không, hệ thống.
- Không dùng ký tự lạ, không dùng tiếng Trung, không dùng pinyin.
- Không lặp keyword gần giống nhau.

Chỉ trả về một JSON object hợp lệ, không Markdown, không giải thích thêm.
Trường description phải là đoạn mô tả tiếng Việt hoàn chỉnh về truyện, không được dùng placeholder như "...".
Trường keywords phải là mảng gồm đúng 6 keyword tiếng Việt hoàn chỉnh, mỗi keyword đúng 2 từ.
Trường completion_status chỉ được là "Hoàn thành", "Chưa hoàn thành" hoặc "Không chắc".
Trường completion_confidence chỉ được là "high", "medium" hoặc "low".
Chỉ chọn "Chưa hoàn thành" với confidence "high" khi đoạn cuối cho thấy truyện đang dang dở rõ ràng.
Nếu không đủ căn cứ, chọn "Không chắc" và confidence "low".
"""


def contains_cjk(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value))


def normalize_keyword(keyword: str) -> str:
    keyword = clean_text(keyword)
    keyword = keyword.strip(" ,.;:-\"'")
    return keyword


def validate_ai_metadata(description: str, keywords: list[str]) -> bool:
    if len(description.split()) < 80:
        return False
    if contains_cjk(description):
        return False
    if len(keywords) != 6:
        return False

    seen = set()
    for keyword in keywords:
        normalized = normalize_keyword(keyword)
        lowered = normalized.lower()
        if not normalized or contains_cjk(normalized):
            return False
        if lowered in seen:
            return False
        if len(normalized.split()) != 2:
            return False
        if any(blocked in lowered for blocked in BLOCKED_KEYWORD_PARTS):
            return False
        seen.add(lowered)

    return True


def metadata_validation_reason(description: str, keywords: list[str]) -> str:
    if len(description.split()) < 80:
        return f"description chỉ có {len(description.split())} từ (cần tối thiểu 80)"
    if contains_cjk(description):
        return "description chứa ký tự tiếng Trung"
    if len(keywords) != 6:
        return f"có {len(keywords)} keyword (cần đúng 6)"
    for keyword in keywords:
        normalized = normalize_keyword(keyword)
        lowered = normalized.lower()
        if not normalized or contains_cjk(normalized):
            return f"keyword không hợp lệ: {keyword!r}"
        if len(normalized.split()) != 2:
            return f"keyword phải đúng 2 từ: {keyword!r}"
        if any(blocked in lowered for blocked in BLOCKED_KEYWORD_PARTS):
            return f"keyword chứa tag bị cấm: {keyword!r}"
    if len({normalize_keyword(keyword).lower() for keyword in keywords}) != 6:
        return "keyword bị trùng"
    return "không xác định"


def parse_ai_metadata(output: str) -> tuple[str, list[str], str, str] | None:
    description_match = re.search(
        r"(?:\*{0,2}\s*)Description\s*:\s*(.+?)(?:\n\s*\*{0,2}\s*Keywords\s*:|$)",
        output,
        flags=re.IGNORECASE | re.DOTALL,
    )
    keywords_match = re.search(
        r"(?:\*{0,2}\s*)Keywords\s*:\s*(.+)$",
        output,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not description_match or not keywords_match:
        return None

    description = clean_text(description_match.group(1).strip().strip("\""))
    raw_keywords = re.sub(r"(?:^|\n)\s*[-*\d.)]+\s*", "\n", keywords_match.group(1))
    raw_keywords = raw_keywords.replace("\n", ",")
    keywords = [normalize_keyword(part) for part in raw_keywords.split(",")]
    keywords = [keyword for keyword in keywords if keyword]

    if not validate_ai_metadata(description, keywords):
        return None

    return description, keywords, "Không chắc", "low"


def generate_ai_metadata(
    title: str,
    author: str,
    story_context: str,
    ending_context: str,
    chapter_count: int,
    provider: str,
    model: str,
    ollama_url: str,
    timeout: int,
    gemini_api_key: str,
    grok_api_key: str,
    groq_api_key: str,
) -> tuple[str, list[str], str, str] | None:
    prompt = build_ollama_prompt(title, author, story_context, ending_context, chapter_count)
    strict_provider = provider in {"gemini", "grok", "groq"}
    if provider == "gemini":
        if not gemini_api_key:
            raise RuntimeError("Thiếu GEMINI_API_KEY trong importer/.env.")
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.25,
                "maxOutputTokens": 700,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "description": {"type": "STRING"},
                        "keywords": {
                            "type": "ARRAY",
                            "minItems": 6,
                            "maxItems": 6,
                            "items": {"type": "STRING"},
                        },
                        "completion_status": {
                            "type": "STRING",
                            "enum": ["Hoàn thành", "Chưa hoàn thành", "Không chắc"],
                        },
                        "completion_confidence": {
                            "type": "STRING",
                            "enum": ["high", "medium", "low"],
                        },
                    },
                    "required": [
                        "description", "keywords", "completion_status", "completion_confidence"
                    ],
                },
            },
        }
    elif provider == "grok":
        if not grok_api_key:
            raise RuntimeError("Thiếu GROK_API_KEY trong importer/.env.")
        endpoint = "https://api.x.ai/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.25,
            "max_tokens": 700,
        }
    elif provider == "groq":
        if not groq_api_key:
            raise RuntimeError("Thiếu GROQ_API_KEY trong importer/.env.")
        endpoint = GROQ_API_URL
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Tạo metadata SEO tiếng Việt và trả về đúng JSON schema được cung cấp.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.25,
            "max_tokens": 2048,
            "reasoning_effort": "low",
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "book_seo_metadata",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "keywords": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "pattern": r"^\S+\s+\S+$",
                                },
                                "minItems": 6,
                                "maxItems": 6,
                            },
                            "completion_status": {
                                "type": "string",
                                "enum": ["Hoàn thành", "Chưa hoàn thành", "Không chắc"],
                            },
                            "completion_confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                            },
                        },
                        "required": [
                            "description", "keywords", "completion_status", "completion_confidence"
                        ],
                        "additionalProperties": False,
                    },
                },
            },
        }
    else:
        endpoint = ollama_url
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": 0.25, "num_predict": 700},
        }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "tienhiep-batch-importer/1.0",
    }
    if provider == "gemini":
        headers["x-goog-api-key"] = gemini_api_key
    if provider in {"grok", "groq"}:
        api_key = grok_api_key if provider == "grok" else groq_api_key
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")

    max_rate_limit_retries = 3
    for attempt in range(max_rate_limit_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if provider == "groq" and exc.code == 429 and attempt < max_rate_limit_retries:
                retry_after = exc.headers.get("Retry-After", "")
                match = re.search(r"try again in\s+([\d.]+)s", body, flags=re.IGNORECASE)
                try:
                    wait_seconds = float(retry_after)
                except (TypeError, ValueError):
                    wait_seconds = float(match.group(1)) if match else 30.0
                wait_seconds = max(wait_seconds + 3.0, 5.0)
                print(
                    f"⏳ Groq đạt giới hạn token/phút. Chờ {wait_seconds:.1f}s "
                    f"rồi thử lại ({attempt + 1}/{max_rate_limit_retries})..."
                )
                time.sleep(wait_seconds)
                continue

            message = f"API {provider} lỗi HTTP {exc.code}: {body}"
            if provider == "groq" and exc.code == 403 and "1010" in body:
                message += (
                    " (Groq/Cloudflare đã chặn request theo IP hoặc chữ ký client; "
                    "hãy thử lại sau khi cập nhật script, tắt VPN/proxy hoặc đổi mạng.)"
                )
            if strict_provider:
                raise RuntimeError(message) from exc
            print(f"⚠️  {message}, dùng SEO template fallback.")
            return None
        except Exception as exc:
            message = f"API {provider} lỗi: {exc}"
            if strict_provider:
                raise RuntimeError(message) from exc
            print(f"⚠️  {message}, dùng SEO template fallback.")
            return None

    if provider == "gemini":
        output = "".join(
            part.get("text", "")
            for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        )
    elif provider in {"grok", "groq"}:
        output = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    else:
        output = data.get("response", "")
    parsed = None
    if provider in {"gemini", "groq"}:
        try:
            structured_text = output.strip()
            structured_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", structured_text, flags=re.IGNORECASE)
            if not structured_text.startswith("{"):
                start = structured_text.find("{")
                end = structured_text.rfind("}")
                if start >= 0 and end > start:
                    structured_text = structured_text[start : end + 1]
            structured = json.loads(structured_text)
            description = clean_text(structured.get("description", ""))
            keywords = [normalize_keyword(str(value)) for value in structured.get("keywords", [])]
            completion_status = clean_text(structured.get("completion_status", ""))
            completion_confidence = clean_text(structured.get("completion_confidence", "")).lower()
            if (
                validate_ai_metadata(description, keywords)
                and completion_status in {"Hoàn thành", "Chưa hoàn thành", "Không chắc"}
                and completion_confidence in {"high", "medium", "low"}
            ):
                parsed = (description, keywords, completion_status, completion_confidence)
        except (json.JSONDecodeError, AttributeError, TypeError):
            parsed = None
    if parsed is None:
        parsed = parse_ai_metadata(output)
    if not parsed:
        message = f"API {provider} trả metadata không đạt format/chất lượng."
        if strict_provider:
            preview = clean_text(output, "<không có nội dung>")[:1200]
            reason = (
                "không đọc được JSON hoặc " + metadata_validation_reason(description, keywords)
                if provider in {"gemini", "groq"} and "description" in locals()
                else "không đọc được JSON"
            )
            raise RuntimeError(f"{message} Lý do: {reason} Phản hồi mẫu: {preview}")
        print(f"⚠️  {message} Dùng SEO template fallback.")
        return None

    return parsed


def write_auto_book_info(
    book_dir: Path,
    ranking: int,
    use_ai_seo: bool,
    ai_provider: str,
    ollama_model: str,
    ollama_url: str,
    ollama_timeout: int,
    gemini_api_key: str,
    grok_api_key: str,
    groq_api_key: str,
):
    info = read_book_info(book_dir)
    title = clean_text(info.get("title", ""), "Truyện Không Tên")
    author = clean_text(info.get("author", ""), "Chưa rõ")
    story_context = read_story_context(book_dir)
    ending_context = read_ending_context(book_dir)
    chapter_count = len(list_chapter_paths(book_dir))
    metadata = None

    if use_ai_seo:
        print(f"🤖 Đang tạo SEO bằng {ai_provider} model {ollama_model}...")
        metadata = generate_ai_metadata(
            clean_title_for_seo(title), author, story_context,
            ending_context, chapter_count,
            ai_provider, ollama_model, ollama_url, ollama_timeout,
            gemini_api_key, grok_api_key, groq_api_key,
        )

    if metadata:
        description, keywords, completion_status, completion_confidence = metadata
        status = (
            "Đang ra"
            if completion_status == "Chưa hoàn thành" and completion_confidence == "high"
            else "Hoàn thành"
        )
        print(
            f"✅ Đã tạo SEO bằng AI. Đánh giá trạng thái: {completion_status} "
            f"({completion_confidence}) → ghi {status}."
        )
    else:
        keywords = build_seo_keywords(title, author)
        description = build_seo_description(title, author, keywords)
        status = "Hoàn thành"

    lines = [
        f"title={title}",
        f"author={author}",
        f"status={status}",
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

    title = epub_to_md.metadata_text(
        book,
        "DC",
        "title",
        epub_to_md.epub_filename_title(str(epub_path)),
    )
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


def read_batch_marker(book_dir: Path) -> dict:
    marker_path = book_dir / BATCH_MARKER_FILE
    try:
        return json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def mark_book_uploaded(book_dir: Path) -> None:
    marker_path = book_dir / BATCH_MARKER_FILE
    marker = read_batch_marker(book_dir)
    marker["uploaded_d1_r2"] = True
    marker["uploaded_at"] = datetime.now(timezone.utc).isoformat()
    marker_path.write_text(
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def remove_book_from_manifest(output_dir: Path, book_dir: Path) -> None:
    manifest_path = output_dir / BATCH_MANIFEST_FILE
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    target = str(book_dir.resolve())
    manifest["book_dirs"] = [
        raw_path
        for raw_path in manifest.get("book_dirs", [])
        if str(Path(raw_path).expanduser().resolve()) != target
    ]
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def is_book_fully_uploaded(book_dir: Path) -> bool:
    if read_batch_marker(book_dir).get("uploaded_d1_r2") is True:
        return True

    try:
        import upload_new_d1_r2

        info = read_book_info(book_dir)
        existing = upload_new_d1_r2.get_existing_book(info["title"])
        if not existing:
            return False
        local_numbers = {
            int(match.group(1))
            for path in list_chapter_paths(book_dir)
            if (match := re.match(r"^(\d+)_", path.name))
        }
        if not local_numbers:
            return False
        return int(existing.get("chapter_count") or 0) >= len(local_numbers)
    except Exception as exc:
        print(f"⚠️  Không thể đối chiếu D1 cho {book_dir.name}: {exc}")
        return False


def get_book_title(book_dir: Path) -> str:
    fallback = book_dir.name.removesuffix("_Translated").replace("_", " ")
    return clean_text(read_book_info(book_dir).get("title") or "", fallback)


def filter_supabase_duplicates(book_dirs: list[Path]) -> tuple[list[Path], list[tuple[Path, dict]]]:
    supabase_books = fetch_supabase_title_slugs()
    if not supabase_books:
        return book_dirs, []

    uploadable: list[Path] = []
    skipped: list[tuple[Path, dict]] = []
    for book_dir in book_dirs:
        title = get_book_title(book_dir)
        matched = supabase_books.get(slugify(title))
        if matched:
            skipped.append((book_dir, matched))
        else:
            uploadable.append(book_dir)

    return uploadable, skipped


def list_epub_files(epub_dir: Path) -> list[Path]:
    return sorted(
        [path for path in epub_dir.iterdir() if path.is_file() and path.suffix.lower() == ".epub"],
        key=lambda path: path.name.lower(),
    )


def convert_epub(
    epub_path: Path,
    output_dir: Path,
    ranking: int,
    allow_missing_chapters: int | None,
    use_ai_seo: bool,
    ai_provider: str,
    ollama_model: str,
    ollama_url: str,
    ollama_timeout: int,
    gemini_api_key: str,
    grok_api_key: str,
    groq_api_key: str,
    batch_id: str,
) -> Path | None:
    converter_log = io.StringIO()
    with contextlib.redirect_stdout(converter_log):
        book_dir = epub_to_md.convert_to_chapters(str(epub_path), str(output_dir))

    summary = converter_log.getvalue()
    if not book_dir:
        error_lines = [line.strip() for line in summary.splitlines() if "❌" in line]
        reason = error_lines[-1] if error_lines else "converter không tạo được thư mục output"
        raise RuntimeError(f"Convert EPUB thất bại: {reason}")

    total_match = re.search(r"Tổng\s+(\d+)\s+chương", summary)
    total_chapters = int(total_match.group(1)) if total_match else 0
    if total_chapters <= 0:
        raise RuntimeError("Convert EPUB không tạo được chương nào.")

    created_match = re.search(r"Tạo mới\s+(\d+)\s+file,\s+bỏ qua\s+(\d+)\s+file", summary)
    created = int(created_match.group(1)) if created_match else None
    existing = int(created_match.group(2)) if created_match else None
    print(
        f"✅ Convert thành công: {total_chapters} chương, "
        f"{created if created is not None else '?'} file mới, "
        f"{existing if existing is not None else '?'} file đã có."
    )

    try:
        epub_book = epub_to_md.read_epub_resilient(str(epub_path))
        expected = len(epub_to_md.collect_toc_chapter_titles(epub_book))
    except Exception as exc:
        raise RuntimeError(f"Không kiểm tra được mục lục EPUB: {exc}") from exc
    if expected and total_chapters < expected:
        missing = expected - total_chapters
        message = (
            f"Convert thiếu chương: EPUB có {expected} mục trong mục lục, "
            f"nhưng chỉ tạo được {total_chapters} chương (thiếu {missing})."
        )
        if allow_missing_chapters is not None and missing > allow_missing_chapters:
            raise RuntimeError(message)
        if allow_missing_chapters is None:
            print(f"⚠️  {message} Tiếp tục vì kiểm tra số chương đang ở chế độ cảnh báo.")
        else:
            print(f"⚠️  {message} Tiếp tục vì đã cho phép thiếu tối đa {allow_missing_chapters} chương.")

    book_dir_path = Path(book_dir)
    write_auto_book_info(
        book_dir_path,
        ranking,
        use_ai_seo,
        ai_provider,
        ollama_model,
        ollama_url,
        ollama_timeout,
        gemini_api_key,
        grok_api_key,
        groq_api_key,
    )
    write_batch_marker(book_dir_path, batch_id, epub_path, ranking, use_ai_seo, ollama_model)
    print(f"📝 Đã ghi book_info SEO: {book_dir_path / 'book_info.txt'}")
    return book_dir_path


def upload_book(book_dir: Path, allow_supabase_duplicate: bool = False) -> bool:
    try:
        from dotenv import load_dotenv

        load_dotenv(SCRIPT_DIR / ".env")
    except Exception:
        pass

    import upload_new_d1_r2

    return upload_new_d1_r2.upload_chapters_new(
        str(book_dir),
        allow_supabase_duplicate=allow_supabase_duplicate,
    )


def main():
    try:
        from dotenv import load_dotenv

        load_dotenv(SCRIPT_DIR / ".env")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="Tự động convert folder nhiều EPUB, ghi SEO book_info.txt và upload truyện mới lên D1 + R2."
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
        help="Chỉ convert và ghi book_info.txt, chưa upload lên D1 + R2.",
    )
    parser.add_argument(
        "--upload-only",
        action="store_true",
        help="Bỏ qua convert, chỉ upload các folder trong manifest batch mới nhất.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ in danh sách sẽ xử lý, không convert và không upload.",
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
        "--convert-limit",
        type=int,
        default=None,
        help="Chỉ convert tối đa N file EPUB trong batch.",
    )
    parser.add_argument(
        "--convert-skip",
        type=int,
        default=0,
        help="Bỏ qua N file EPUB đầu khi convert batch.",
    )
    parser.add_argument(
        "--allow-missing-chapters",
        type=int,
        default=None,
        help=(
            "Đặt số chương tối đa được phép thiếu so với mục lục; vượt quá sẽ dừng. "
            "Mặc định không giới hạn, chỉ cảnh báo và tiếp tục."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed random ranking để lần chạy sau sinh ranking giống nhau nếu cần.",
    )
    parser.add_argument(
        "--ai-provider",
        choices=("ollama", "gemini", "grok", "groq"),
        default=os.environ.get("AI_PROVIDER", "ollama"),
        help="Provider tạo SEO: ollama, gemini, grok (xAI) hoặc groq. Có thể đặt AI_PROVIDER trong .env.",
    )
    parser.add_argument(
        "--ollama-model",
        "--ai-model",
        dest="ollama_model",
        default=os.environ.get("AI_MODEL", DEFAULT_OLLAMA_MODEL),
        help=f"Model AI dùng để viết SEO. Mặc định: {DEFAULT_OLLAMA_MODEL}",
    )
    parser.add_argument(
        "--gemini-api-key",
        default=os.environ.get("GEMINI_API_KEY", ""),
        help="Gemini API key; nên đặt GEMINI_API_KEY trong importer/.env.",
    )
    parser.add_argument(
        "--grok-api-key",
        default=os.environ.get("GROK_API_KEY", ""),
        help="Grok API key; nên đặt GROK_API_KEY trong importer/.env.",
    )
    parser.add_argument(
        "--groq-api-key",
        default=os.environ.get("GROQ_API_KEY", ""),
        help="Groq API key; nên đặt GROQ_API_KEY trong importer/.env.",
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
        "--ai-delay",
        type=float,
        default=float(os.environ.get("AI_DELAY_SECONDS", "30")),
        help="Số giây chờ giữa hai truyện khi dùng AI online. Mặc định: 30.",
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
    parser.add_argument(
        "--allow-supabase-duplicates",
        action="store_true",
        help="Cho phép upload lên D1/R2 cả truyện đã tồn tại trong Supabase cũ.",
    )
    args = parser.parse_args()

    if args.convert_only and args.upload_only:
        print("❌ Chỉ dùng một trong hai option: --convert-only hoặc --upload-only.")
        sys.exit(1)
    if args.dry_run and not args.upload_only:
        print("❌ --dry-run hiện chỉ dùng cùng --upload-only để xem danh sách sẽ upload.")
        sys.exit(1)
    if args.upload_limit is not None and args.upload_limit < 1:
        print("❌ --upload-limit phải lớn hơn 0.")
        sys.exit(1)
    if args.convert_limit is not None and args.convert_limit < 1:
        print("❌ --convert-limit phải lớn hơn 0.")
        sys.exit(1)
    if args.convert_skip < 0:
        print("❌ --convert-skip không được âm.")
        sys.exit(1)
    if args.allow_missing_chapters is not None and args.allow_missing_chapters < 0:
        print("❌ --allow-missing-chapters không được âm.")
        sys.exit(1)
    if args.ai_delay < 0:
        print("❌ --ai-delay không được âm.")
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

        already_uploaded = []
        pending_book_dirs = []
        print("🔎 Đang đối chiếu manifest với D1 để bỏ qua truyện đã upload...")
        for book_dir in book_dirs:
            if is_book_fully_uploaded(book_dir):
                if not args.dry_run:
                    mark_book_uploaded(book_dir)
                    remove_book_from_manifest(output_dir, book_dir)
                already_uploaded.append(book_dir)
            else:
                pending_book_dirs.append(book_dir)
        book_dirs = pending_book_dirs
        if already_uploaded:
            print(f"✅ Tự động bỏ qua {len(already_uploaded)} truyện đã upload đầy đủ lên D1/R2.")
        if not book_dirs:
            print(f"🏆 Cả {total_in_manifest} truyện trong manifest đã upload xong. Không còn gì để làm.")
            return

        if not args.allow_supabase_duplicates:
            book_dirs, skipped_supabase = filter_supabase_duplicates(book_dirs)
            if skipped_supabase:
                print(f"🛡️  Đã skip {len(skipped_supabase)} truyện vì đã có trong Supabase cũ:")
                for book_dir, matched in skipped_supabase:
                    print(
                        f"   - {get_book_title(book_dir)} "
                        f"(Supabase ID {matched.get('id')}, {matched.get('chapter_count') or 0} chương)"
                    )
                print("   Nếu cố ý muốn upload trùng lên D1/R2, thêm --allow-supabase-duplicates.")

        if args.upload_skip:
            book_dirs = book_dirs[args.upload_skip:]
        if args.upload_limit is not None:
            book_dirs = book_dirs[:args.upload_limit]
        if not book_dirs:
            print(f"⚠️  Không còn truyện nào để upload sau --upload-skip trong batch {total_in_manifest} truyện.")
            return

        print(
            f"📌 Upload-only: sẽ upload {len(book_dirs)}/{total_in_manifest} "
            "folder trong batch mới nhất sau khi lọc trùng Supabase."
        )
        print("📚 Danh sách sẽ upload:")
        for index, book_dir in enumerate(book_dirs, 1):
            print(f"   {index}. {book_dir.name}")

        if args.dry_run:
            print("\n✅ Dry-run xong. Chưa upload truyện nào.")
            return
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

        total_epub_files = len(epub_files)
        epub_files = epub_files[args.convert_skip:]
        if args.convert_limit is not None:
            epub_files = epub_files[:args.convert_limit]
        if not epub_files:
            print(f"⚠️  Không còn EPUB để convert sau --convert-skip {args.convert_skip}.")
            return

        print(
            f"📚 Sẽ convert {len(epub_files)}/{total_epub_files} file EPUB "
            f"(bỏ qua {args.convert_skip} file đầu)."
        )
        batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        book_dirs = []
        write_batch_manifest(output_dir, batch_id, book_dirs)
        for index, epub_path in enumerate(epub_files, 1):
            expected_book_dir = get_epub_output_dir(epub_path, output_dir)
            if expected_book_dir and expected_book_dir.exists() and not args.overwrite_existing:
                print(f"\n{'=' * 70}")
                print(f"⏭️  [{index}/{len(epub_files)}] Bỏ qua vì folder đã tồn tại: {expected_book_dir}")
                print("   Nếu muốn convert lại folder này, chạy thêm --overwrite-existing.")
                continue

            ranking = random.randint(200, 1000)
            print(f"\n{'=' * 70}")
            print(f"📖 [{index}/{len(epub_files)}] Convert: {epub_path.name} | ranking={ranking}")
            try:
                book_dir = convert_epub(
                    epub_path,
                    output_dir,
                    ranking,
                    args.allow_missing_chapters,
                    not args.no_ai_seo,
                    args.ai_provider,
                    args.ollama_model,
                    args.ollama_url,
                    args.ollama_timeout,
                    args.gemini_api_key,
                    args.grok_api_key,
                    args.groq_api_key,
                    batch_id,
                )
            except RuntimeError as exc:
                print(f"\n❌ Batch dừng tại {epub_path.name}: {exc}")
                print("   Không dùng SEO fallback. Sửa API key/quota rồi chạy lại nhóm này.")
                raise SystemExit(1) from exc
            if book_dir:
                book_dirs.append(book_dir)
                write_batch_manifest(output_dir, batch_id, book_dirs)
                if (
                    index < len(epub_files)
                    and not args.no_ai_seo
                    and args.ai_provider in {"gemini", "grok", "groq"}
                    and args.ai_delay > 0
                ):
                    print(f"⏳ Chờ {args.ai_delay:g}s trước truyện tiếp theo để tránh rate limit...")
                    time.sleep(args.ai_delay)

        write_batch_manifest(output_dir, batch_id, book_dirs)
        print(f"\n📌 Đã ghi manifest batch mới nhất: {output_dir / BATCH_MANIFEST_FILE}")

    if args.convert_only:
        print(f"\n✅ Convert xong {len(book_dirs)} truyện. Chưa upload vì đang dùng --convert-only.")
        return

    print(f"\n🚀 Bắt đầu upload {len(book_dirs)} truyện mới lên Cloudflare D1 + R2...")
    completed_uploads = 0
    for index, book_dir in enumerate(book_dirs, 1):
        print(f"\n{'=' * 70}")
        print(f"⬆️  [{index}/{len(book_dirs)}] Upload: {book_dir}")
        uploaded = upload_book(book_dir, allow_supabase_duplicate=args.allow_supabase_duplicates)
        if not uploaded:
            print(f"❌ Upload chưa hoàn tất: {book_dir.name}. Giữ lại trong manifest để chạy tiếp.")
            raise SystemExit(1)
        mark_book_uploaded(book_dir)
        remove_book_from_manifest(output_dir, book_dir)
        completed_uploads += 1
        print("📝 Đã đánh dấu uploaded_d1_r2=true và xóa truyện khỏi danh sách chờ upload.")

    print(f"\n🏆 Hoàn tất batch: {completed_uploads} truyện.")


if __name__ == "__main__":
    main()
