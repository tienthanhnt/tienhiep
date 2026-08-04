#!/usr/bin/env python3
import argparse
import csv
import os
import re
import sys
import time
from datetime import datetime
from time import perf_counter
from typing import Any

import requests


OLLAMA_BASE_URL = "http://localhost:11434/api"
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/tags"

SOURCE_DIR_DEFAULT = "chapters/Xich_Tam_Tuan_Thien"
OUTPUT_ROOT_DEFAULT = "chapters/benchmark_results"
BENCHMARK_CSV_DEFAULT = "benchmark.csv"

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


CSV_FIELDS = [
    "timestamp",
    "model",
    "filename",
    "mode",
    "chunk_size",
    "overlap_paragraphs",
    "chunk_count",
    "completed_chunks",
    "failed_chunk",
    "num_ctx",
    "num_predict",
    "temperature",
    "source_chars",
    "output_chars",
    "length_ratio",
    "source_paragraphs",
    "output_paragraphs",
    "paragraph_ratio",
    "prompt_tokens",
    "output_tokens",
    "wall_seconds",
    "ollama_seconds",
    "load_seconds",
    "prompt_eval_seconds",
    "generation_seconds",
    "prompt_tokens_per_second",
    "output_tokens_per_second",
    "done_reason",
    "validation",
    "error",
    "output_path",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Chạy benchmark tất cả model Ollama đã cài bằng hai chế độ: "
            "toàn chương và chia nhỏ."
        )
    )
    parser.add_argument(
        "--source-dir",
        default=SOURCE_DIR_DEFAULT,
        help="Thư mục chứa các chương Markdown.",
    )
    parser.add_argument(
        "--output-root",
        default=OUTPUT_ROOT_DEFAULT,
        help="Thư mục gốc lưu đầu ra của từng model và chế độ.",
    )
    parser.add_argument(
        "--benchmark-csv",
        default=BENCHMARK_CSV_DEFAULT,
        help="Một file CSV duy nhất lưu toàn bộ kết quả benchmark.",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=None,
        help="Chỉ benchmark các file được chỉ định.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Số chương đầu tiên để benchmark khi không truyền --files.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help=(
            "Danh sách model cần chạy. Nếu bỏ qua, script tự lấy toàn bộ "
            "model đang cài từ Ollama."
        ),
    )
    parser.add_argument(
        "--exclude-models",
        nargs="*",
        default=[],
        help="Các model cần loại khỏi benchmark.",
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
        "--full-num-ctx",
        type=int,
        default=65536,
        help="Context cho chế độ full.",
    )
    parser.add_argument(
        "--full-num-predict",
        type=int,
        default=32768,
        help="Giới hạn đầu ra cho chế độ full.",
    )
    parser.add_argument(
        "--chunk-num-ctx",
        type=int,
        default=16384,
        help="Context cho chế độ chunked.",
    )
    parser.add_argument(
        "--chunk-num-predict",
        type=int,
        default=6000,
        help="Giới hạn đầu ra cho mỗi chunk.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.15,
        help="Temperature dùng chung để so sánh công bằng.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed dùng chung cho các model.",
    )
    parser.add_argument(
        "--keep-alive",
        default="30m",
        help="Thời gian giữ model trong bộ nhớ khi xử lý cùng model.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=7200,
        help="Timeout cho mỗi request, tính bằng giây.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Chạy lại và ghi đè cả khi file đầu ra đã tồn tại.",
    )
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)


def get_installed_models(
    session: requests.Session,
    explicitly_requested: list[str] | None,
    excluded: list[str],
    timeout: int,
) -> list[str]:
    if explicitly_requested:
        models = explicitly_requested
    else:
        response = session.get(OLLAMA_TAGS_URL, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        models = [
            item["name"]
            for item in data.get("models", [])
            if item.get("name")
        ]

    excluded_set = set(excluded)
    models = [model for model in models if model not in excluded_set]

    # Giữ thứ tự nhưng loại trùng.
    return list(dict.fromkeys(models))


def get_source_files(args: argparse.Namespace) -> list[str]:
    if args.files:
        return args.files

    files = sorted(
        filename
        for filename in os.listdir(args.source_dir)
        if filename.endswith(".md")
    )

    if args.limit is not None:
        files = files[: args.limit]

    return files


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

        # Một đoạn riêng lẻ dài hơn max_chars vẫn được giữ nguyên để không cắt câu.
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


def create_full_prompt(content: str) -> str:
    return f"""
Hãy biên tập đầy đủ toàn bộ chương truyện trong thẻ <CHUONG_GOC>.

- Biên tập từ câu đầu tiên đến câu cuối cùng.
- Không bỏ qua bất kỳ đoạn nào.
- Không tóm tắt hoặc phân tích.
- Không thêm lời dẫn.
- Giữ nguyên tên riêng và thuật ngữ.
- Độ dài đầu ra phải gần với độ dài đầu vào.
- Câu đầu và câu cuối phải tương ứng với nguồn.

<CHUONG_GOC>
{content}
</CHUONG_GOC>

Chỉ trả về toàn bộ chương truyện đã biên tập.
""".strip()


def create_chunk_prompt(
    chunk: str,
    chunk_index: int,
    total_chunks: int,
    context: str,
) -> str:
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
        "tóm tắt",
        "tóm tắt nội dung",
        "phân tích",
        "phân tích chi tiết",
        "nhận xét",
        "ý nghĩa",
        "ý nghĩa ẩn dụ",
        "câu hỏi mở",
        "dưới đây là",
        "nội dung chính",
        "nội dung đoạn văn",
        "đoạn văn mô tả",
    ]

    for prefix in forbidden_prefixes:
        if normalized.startswith(prefix):
            raise ValueError(
                f"Model trả về nội dung không hợp lệ, bắt đầu bằng '{prefix}'."
            )

    source_length = len(source.strip())
    edited_length = len(edited.strip())

    if source_length == 0:
        raise ValueError("Nội dung nguồn rỗng.")

    length_ratio = edited_length / source_length
    if length_ratio < 0.60:
        raise ValueError(
            f"Kết quả quá ngắn: chỉ bằng {length_ratio:.1%} nguồn."
        )

    source_paragraphs = split_into_paragraphs(source)
    edited_paragraphs = split_into_paragraphs(edited)

    if len(source_paragraphs) >= 5:
        ratio = len(edited_paragraphs) / len(source_paragraphs)
        if ratio < 0.45:
            raise ValueError(
                "Số đoạn đầu ra quá ít: "
                f"{len(edited_paragraphs)}/{len(source_paragraphs)}."
            )


def empty_metrics() -> dict[str, Any]:
    return {
        "prompt_tokens": 0,
        "output_tokens": 0,
        "total_duration_ns": 0,
        "load_duration_ns": 0,
        "prompt_eval_duration_ns": 0,
        "eval_duration_ns": 0,
        "done_reasons": [],
    }


def add_metrics(metrics: dict[str, Any], response: dict[str, Any]) -> None:
    metrics["prompt_tokens"] += response.get("prompt_eval_count", 0)
    metrics["output_tokens"] += response.get("eval_count", 0)
    metrics["total_duration_ns"] += response.get("total_duration", 0)
    metrics["load_duration_ns"] += response.get("load_duration", 0)
    metrics["prompt_eval_duration_ns"] += response.get(
        "prompt_eval_duration", 0
    )
    metrics["eval_duration_ns"] += response.get("eval_duration", 0)
    metrics["done_reasons"].append(response.get("done_reason", "unknown"))


def call_ollama(
    session: requests.Session,
    model: str,
    prompt: str,
    num_ctx: int,
    num_predict: int,
    args: argparse.Namespace,
) -> tuple[str, dict[str, Any]]:
    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "keep_alive": args.keep_alive,
        "options": {
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "temperature": args.temperature,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.03,
            "seed": args.seed,
        },
    }

    response = session.post(
        OLLAMA_GENERATE_URL,
        json=payload,
        timeout=args.timeout,
    )
    response.raise_for_status()
    result = response.json()
    return clean_model_output(result.get("response", "")), result


def unload_model(
    session: requests.Session,
    model: str,
    timeout: int,
) -> None:
    try:
        session.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": model,
                "prompt": "",
                "stream": False,
                "keep_alive": 0,
            },
            timeout=timeout,
        )
    except requests.RequestException:
        # Không làm hỏng benchmark chỉ vì unload thất bại.
        pass


def run_full(
    session: requests.Session,
    model: str,
    content: str,
    args: argparse.Namespace,
) -> tuple[str, dict[str, Any], int, int]:
    metrics = empty_metrics()
    output, result = call_ollama(
        session=session,
        model=model,
        prompt=create_full_prompt(content),
        num_ctx=args.full_num_ctx,
        num_predict=args.full_num_predict,
        args=args,
    )
    add_metrics(metrics, result)
    validate_edited_text(content, output)
    return output, metrics, 1, 1


def run_chunked(
    session: requests.Session,
    model: str,
    content: str,
    args: argparse.Namespace,
) -> tuple[str, dict[str, Any], int, int]:
    chunks = split_into_chunks(content, args.chunk_size)
    metrics = empty_metrics()
    outputs: list[str] = []
    completed = 0
    prior_chunk = ""

    for index, chunk in enumerate(chunks, start=1):
        print(
            f"      chunk {index}/{len(chunks)} "
            f"({len(chunk)} characters)"
        )

        context = previous_context(
            prior_chunk,
            args.overlap_paragraphs,
        )

        output, result = call_ollama(
            session=session,
            model=model,
            prompt=create_chunk_prompt(
                chunk=chunk,
                chunk_index=index,
                total_chunks=len(chunks),
                context=context,
            ),
            num_ctx=args.chunk_num_ctx,
            num_predict=args.chunk_num_predict,
            args=args,
        )

        add_metrics(metrics, result)
        validate_edited_text(chunk, output)

        outputs.append(output.strip())
        completed += 1
        prior_chunk = chunk

    merged = "\n\n".join(outputs)
    validate_edited_text(content, merged)
    return merged, metrics, len(chunks), completed


def append_csv(
    csv_path: str,
    *,
    model: str,
    filename: str,
    mode: str,
    source: str,
    output: str,
    metrics: dict[str, Any],
    wall_seconds: float,
    chunk_count: int,
    completed_chunks: int,
    failed_chunk: str,
    num_ctx: int,
    num_predict: int,
    args: argparse.Namespace,
    validation: str,
    error: str,
    output_path: str,
) -> None:
    file_exists = os.path.exists(csv_path)

    source_chars = len(source)
    output_chars = len(output)
    source_paragraphs = len(split_into_paragraphs(source))
    output_paragraphs = len(split_into_paragraphs(output))

    length_ratio = output_chars / source_chars if source_chars else 0
    paragraph_ratio = (
        output_paragraphs / source_paragraphs
        if source_paragraphs
        else 0
    )

    ollama_seconds = metrics["total_duration_ns"] / 1_000_000_000
    load_seconds = metrics["load_duration_ns"] / 1_000_000_000
    prompt_seconds = (
        metrics["prompt_eval_duration_ns"] / 1_000_000_000
    )
    generation_seconds = metrics["eval_duration_ns"] / 1_000_000_000

    prompt_speed = (
        metrics["prompt_tokens"] / prompt_seconds
        if prompt_seconds > 0
        else 0
    )
    output_speed = (
        metrics["output_tokens"] / generation_seconds
        if generation_seconds > 0
        else 0
    )

    done_reason = "|".join(
        sorted(set(metrics["done_reasons"]))
    )

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "model": model,
        "filename": filename,
        "mode": mode,
        "chunk_size": args.chunk_size if mode == "chunked" else 0,
        "overlap_paragraphs": (
            args.overlap_paragraphs if mode == "chunked" else 0
        ),
        "chunk_count": chunk_count,
        "completed_chunks": completed_chunks,
        "failed_chunk": failed_chunk,
        "num_ctx": num_ctx,
        "num_predict": num_predict,
        "temperature": args.temperature,
        "source_chars": source_chars,
        "output_chars": output_chars,
        "length_ratio": round(length_ratio, 4),
        "source_paragraphs": source_paragraphs,
        "output_paragraphs": output_paragraphs,
        "paragraph_ratio": round(paragraph_ratio, 4),
        "prompt_tokens": metrics["prompt_tokens"],
        "output_tokens": metrics["output_tokens"],
        "wall_seconds": round(wall_seconds, 3),
        "ollama_seconds": round(ollama_seconds, 3),
        "load_seconds": round(load_seconds, 3),
        "prompt_eval_seconds": round(prompt_seconds, 3),
        "generation_seconds": round(generation_seconds, 3),
        "prompt_tokens_per_second": round(prompt_speed, 3),
        "output_tokens_per_second": round(output_speed, 3),
        "done_reason": done_reason,
        "validation": validation,
        "error": error,
        "output_path": output_path,
    }

    with open(csv_path, "a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main() -> int:
    args = parse_args()

    if not os.path.isdir(args.source_dir):
        print(f"Source directory does not exist: {args.source_dir}")
        return 1

    os.makedirs(args.output_root, exist_ok=True)

    with requests.Session() as session:
        try:
            models = get_installed_models(
                session=session,
                explicitly_requested=args.models,
                excluded=args.exclude_models,
                timeout=args.timeout,
            )
        except requests.RequestException as error:
            print(f"Cannot connect to Ollama: {error}")
            return 1

        files = get_source_files(args)

        if not models:
            print("No Ollama models selected.")
            return 1

        if not files:
            print("No Markdown files found.")
            return 1

        print("Models:")
        for model in models:
            print(f"  - {model}")

        print("Files:")
        for filename in files:
            print(f"  - {filename}")

        total_runs = len(models) * len(files) * 2
        current_run = 0

        for model in models:
            print(f"\n=== MODEL: {model} ===")

            for filename in files:
                source_path = os.path.join(args.source_dir, filename)

                with open(source_path, "r", encoding="utf-8") as file:
                    content = file.read()

                for mode in ("full", "chunked"):
                    current_run += 1

                    output_dir = os.path.join(
                        args.output_root,
                        safe_name(model),
                        (
                            "full"
                            if mode == "full"
                            else (
                                f"chunked_{args.chunk_size}"
                                f"_overlap_{args.overlap_paragraphs}"
                            )
                        ),
                    )
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, filename)

                    print(
                        f"\n[{current_run}/{total_runs}] "
                        f"{model} | {mode} | {filename}"
                    )

                    if os.path.exists(output_path) and not args.force:
                        print("  Skipped: output already exists.")
                        continue

                    start = perf_counter()
                    metrics = empty_metrics()
                    output = ""
                    chunk_count = 0
                    completed_chunks = 0
                    failed_chunk = ""
                    validation = "FAIL"
                    error_message = ""

                    try:
                        if mode == "full":
                            (
                                output,
                                metrics,
                                chunk_count,
                                completed_chunks,
                            ) = run_full(
                                session=session,
                                model=model,
                                content=content,
                                args=args,
                            )
                            num_ctx = args.full_num_ctx
                            num_predict = args.full_num_predict
                        else:
                            chunks = split_into_chunks(
                                content,
                                args.chunk_size,
                            )
                            chunk_count = len(chunks)

                            try:
                                (
                                    output,
                                    metrics,
                                    chunk_count,
                                    completed_chunks,
                                ) = run_chunked(
                                    session=session,
                                    model=model,
                                    content=content,
                                    args=args,
                                )
                            except Exception as error:
                                match = re.search(
                                    r"chunk\s+(\d+)/(\d+)",
                                    str(error),
                                    re.IGNORECASE,
                                )
                                if match:
                                    failed_chunk = match.group(1)
                                raise

                            num_ctx = args.chunk_num_ctx
                            num_predict = args.chunk_num_predict

                        with open(
                            output_path,
                            "w",
                            encoding="utf-8",
                        ) as file:
                            file.write(output)

                        validation = "PASS"

                    except Exception as error:
                        error_message = str(error)
                        print(f"  Failed: {error_message}")

                        if mode == "full":
                            num_ctx = args.full_num_ctx
                            num_predict = args.full_num_predict
                        else:
                            num_ctx = args.chunk_num_ctx
                            num_predict = args.chunk_num_predict

                    wall_seconds = perf_counter() - start

                    append_csv(
                        args.benchmark_csv,
                        model=model,
                        filename=filename,
                        mode=mode,
                        source=content,
                        output=output,
                        metrics=metrics,
                        wall_seconds=wall_seconds,
                        chunk_count=chunk_count,
                        completed_chunks=completed_chunks,
                        failed_chunk=failed_chunk,
                        num_ctx=num_ctx,
                        num_predict=num_predict,
                        args=args,
                        validation=validation,
                        error=error_message,
                        output_path=output_path if validation == "PASS" else "",
                    )

                    print(
                        f"  {validation} | "
                        f"{wall_seconds:.2f}s | "
                        f"output={len(output)} chars"
                    )

            # Giải phóng model trước khi chuyển sang model tiếp theo.
            unload_model(session, model, args.timeout)
            time.sleep(2)

    print("\nBenchmark completed.")
    print(f"CSV: {args.benchmark_csv}")
    print(f"Outputs: {args.output_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
