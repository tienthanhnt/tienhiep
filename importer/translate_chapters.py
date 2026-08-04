import os
import sys
import time
import argparse
import requests
import re

parser = argparse.ArgumentParser(
    description="Biên tập truyện convert bằng Ollama (Local AI) với cơ chế Chunking."
)

parser.add_argument(
    "--model",
    type=str,
    help="Tên model Ollama sẽ sử dụng",
    default="gemma3:27b"
)
parser.add_argument(
    "--limit",
    type=int,
    help="Số lượng chương muốn biên tập (dùng để test)",
    default=None
)
parser.add_argument(
    "--files",
    type=str,
    nargs="+",
    help="Danh sách tên file cụ thể muốn biên tập",
    default=None
)
parser.add_argument(
    "--chunk-size",
    type=int,
    default=6000,
    help="Số ký tự tối đa của một chunk.",
)
parser.add_argument(
    "--overlap-paragraphs",
    type=int,
    default=2,
    help="Số đoạn cuối chunk trước dùng làm ngữ cảnh.",
)

parser.add_argument(
    "--source-dir",
    type=str,
    default="chapters/Xich_Tam_Tuan_Thien",
    help="Thư mục chứa các file chương gốc"
)
parser.add_argument(
    "--target-dir",
    type=str,
    default=None,
    help="Thư mục lưu các file chương đã dịch"
)

args = parser.parse_args()

MODEL_NAME = args.model
OLLAMA_API_URL = "http://localhost:11434/api/generate"

SOURCE_DIR = args.source_dir
TARGET_DIR = args.target_dir if args.target_dir else f"{SOURCE_DIR.rstrip('/')}_Translated"

if not os.path.exists(TARGET_DIR):
    os.makedirs(TARGET_DIR)

if args.files:
    files = args.files
else:
    files = sorted([f for f in os.listdir(SOURCE_DIR) if f.endswith(".md")])
    if args.limit:
        files = files[:args.limit]

print(f"Tìm thấy {len(files)} chương cần biên tập.")
print(f"Đang sử dụng Ollama model: {MODEL_NAME}")
print(f"Chế độ Chunking: {args.chunk_size} ký tự/chunk, overlap {args.overlap_paragraphs} đoạn.")


SYSTEM_PROMPT = """
Bạn là một công cụ biên tập truyện chuyên nghiệp, không phải trợ lý trò chuyện.

Văn bản đầu vào là truyện Trung Quốc đã được chuyển ngữ thô sang tiếng Việt,
thường có câu chữ cứng, đảo ngữ, sai ngữ pháp hoặc mang cấu trúc tiếng Trung.

NHIỆM VỤ DUY NHẤT:
Biên tập văn bản đầu vào thành tiếng Việt tự nhiên, trôi chảy, dễ đọc,
phù hợp với văn phong truyện tiên hiệp.

QUY TẮC BẮT BUỘC:
1. Giữ nguyên toàn bộ nội dung, tình tiết, hành động, miêu tả và hội thoại.
2. Không bỏ sót bất kỳ câu, đoạn hoặc chi tiết nào.
3. Không tóm tắt, không rút gọn và không diễn giải nội dung.
4. Không phân tích, bình luận, nhận xét hoặc giải thích.
5. Không tự sáng tác hoặc bổ sung tình tiết không có trong nguồn.
6. Không thay đổi tên nhân vật, địa danh, môn phái, cảnh giới, công pháp,
   chiêu thức, pháp bảo và thuật ngữ riêng.
7. Giữ nguyên thứ tự diễn biến.
8. Giữ nguyên tiêu đề, cấu trúc đoạn và định dạng Markdown.
9. Có thể tái cấu trúc câu để tiếng Việt tự nhiên hơn nhưng phải giữ nguyên ý.
10. Giữ nguyên cách xưng hô phù hợp với quan hệ giữa các nhân vật.
11. Chỉ xuất văn bản truyện đã biên tập.
12. Không thêm lời mở đầu, lời kết luận hoặc tiêu đề phụ.

TUYỆT ĐỐI KHÔNG xuất:
- Tóm tắt nội dung
- Phân tích chi tiết
- Ý nghĩa ẩn dụ
- Nhận xét
- Câu hỏi mở
- Dưới đây là bản dịch
- Dưới đây là nội dung đã chỉnh sửa
""".strip()


def split_into_paragraphs(text: str) -> list[str]:
    return [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]


def split_into_chunks(text: str, max_chars: int) -> list[str]:
    paragraphs = split_into_paragraphs(text)
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        extra = len(paragraph) + (2 if current else 0)

        if current and current_length + extra > max_chars:
            chunks.append("\n\n".join(current))
            current = []
            current_length = 0

        current.append(paragraph)
        current_length += len(paragraph) + (2 if len(current) > 1 else 0)

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def previous_context(chunk: str, paragraph_count: int) -> str:
    if paragraph_count <= 0:
        return ""
    paragraphs = split_into_paragraphs(chunk)
    return "\n\n".join(paragraphs[-paragraph_count:])


def create_chunk_prompt(chunk: str, chunk_index: int, total_chunks: int, context: str) -> str:
    context_block = ""
    if context:
        context_block = f"""
<NGU_CANH_TRUOC>
{context}
</NGU_CANH_TRUOC>

NGU_CANH_TRUOC chỉ dùng để hiểu nhân vật, thuật ngữ và cách xưng hô.
Không được xuất lại nội dung trong NGU_CANH_TRUOC.
""".strip()

    return f"""
Bạn đang biên tập phần {chunk_index}/{total_chunks} của một chương truyện dài.

{context_block}

- Chỉ biên tập nội dung trong NOI_DUNG_CAN_BIEN_TAP.
- Giữ nguyên đầy đủ mọi câu, đoạn, tình tiết và chi tiết.
- Không tóm tắt.
- Không thêm mở đầu hoặc kết luận.
- Không tự viết tiếp phần chưa được cung cấp.
- Giữ nguyên tên riêng, thuật ngữ, xưng hô, cấu trúc đoạn và Markdown.
- Không lặp lại NGU_CANH_TRUOC.

<NOI_DUNG_CAN_BIEN_TAP>
{chunk}
</NOI_DUNG_CAN_BIEN_TAP>

Chỉ trả về nội dung đã biên tập của phần hiện tại.
""".strip()


def clean_model_output(text: str) -> str:
    text = text.strip()
    prefixes = [
        "<CHUONG_DA_BIEN_TAP>",
        "<CHUONG_BIEN_TAP>",
        "<NOI_DUNG_DA_BIEN_TAP>",
        "```markdown",
        "```md",
    ]
    suffixes = [
        "</CHUONG_DA_BIEN_TAP>",
        "</CHUONG_BIEN_TAP>",
        "</NOI_DUNG_DA_BIEN_TAP>",
        "```",
    ]
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].lstrip()
                changed = True
        for suffix in suffixes:
            if text.endswith(suffix):
                text = text[:-len(suffix)].rstrip()
                changed = True
    return text.strip()


def validate_edited_text(source: str, edited: str) -> None:
    if not edited.strip():
        raise ValueError("Ollama trả về nội dung rỗng.")

    normalized = edited.lower().lstrip(" \n\t#*-—_:.")
    forbidden_prefixes = [
        "tóm tắt", "tóm tắt nội dung", "phân tích", "phân tích chi tiết",
        "nhận xét", "ý nghĩa", "ý nghĩa ẩn dụ", "câu hỏi mở",
        "dưới đây là", "nội dung chính", "nội dung đoạn văn", "đoạn văn mô tả",
    ]
    for prefix in forbidden_prefixes:
        if normalized.startswith(prefix):
            raise ValueError(f"Nội dung không hợp lệ, bắt đầu bằng '{prefix}'.")

    source_length = len(source.strip())
    edited_length = len(edited.strip())
    if source_length == 0:
        raise ValueError("Nội dung nguồn rỗng.")

    length_ratio = edited_length / source_length
    if length_ratio < 0.60:
        raise ValueError(f"Kết quả quá ngắn: chỉ bằng {length_ratio:.1%} nguồn.")

    source_paragraphs = split_into_paragraphs(source)
    edited_paragraphs = split_into_paragraphs(edited)

    if len(source_paragraphs) >= 5:
        ratio = len(edited_paragraphs) / len(source_paragraphs)
        if ratio < 0.45:
            raise ValueError(
                f"Số đoạn đầu ra quá ít: {len(edited_paragraphs)}/{len(source_paragraphs)}."
            )


# VÒNG LẶP XỬ LÝ TỪNG FILE
for filename in files:
    source_path = os.path.join(SOURCE_DIR, filename)
    target_path = os.path.join(TARGET_DIR, filename)

    if os.path.exists(target_path):
        print(f"[-] Bỏ qua {filename} (Đã biên tập)")
        continue

    print(f"\n[+] Đang xử lý {filename}...")

    with open(source_path, "r", encoding="utf-8") as f:
        content = f.read()

    chunks = split_into_chunks(content, args.chunk_size)
    outputs = []
    prior_chunk = ""
    has_error = False

    for index, chunk in enumerate(chunks, start=1):
        print(f"    -> Đang dịch phần {index}/{len(chunks)} ({len(chunk)} ký tự)")
        context = previous_context(prior_chunk, args.overlap_paragraphs)
        prompt = create_chunk_prompt(chunk, index, len(chunks), context)

        payload = {
            "model": MODEL_NAME,
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "num_ctx": 16384,
                "num_predict": 6000,
                "temperature": 0.0,
                "top_p": 0.8,
                "top_k": 20,
                "repeat_penalty": 1.03,
                "seed": 42
            }
        }

        try:
            response = requests.post(OLLAMA_API_URL, json=payload)
            response.raise_for_status()
            
            result_json = response.json()
            output_chunk = clean_model_output(result_json.get("response", ""))
            
            # Kiểm chứng chất lượng chunk
            validate_edited_text(chunk, output_chunk)
            
            outputs.append(output_chunk)
            prior_chunk = chunk
            
        except requests.exceptions.ConnectionError:
            print("Lỗi: Không thể kết nối tới Ollama.")
            sys.exit(1)
        except Exception as e:
            print(f"       Lỗi khi dịch phần {index}: {e}")
            has_error = True
            break
            
    if has_error:
        print(f"    -> Bỏ qua {filename} vì có lỗi trong quá trình xử lý chunk.")
        time.sleep(2)
        continue
        
    # Ghép các chunk lại
    merged_output = "\n\n".join(outputs)
    
    try:
        # Kiểm tra lần cuối trên toàn bộ file
        validate_edited_text(content, merged_output)
    except Exception as e:
        print(f"    -> Lỗi Validation khi ghép file {filename}: {e}")
        continue

    # Ghi kết quả
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(merged_output)

    print(f"    -> Hoàn tất lưu {filename}.")

print("\nHoàn thành!")