#!/usr/bin/env python3
"""Safely delete one book and its chapter/cover objects from Cloudflare D1 + R2."""

import argparse
from urllib.parse import urlparse

from dotenv import load_dotenv

from cloudflare_store import create_r2_client, d1_query, d1_rows


def r2_key_from_url(url: str, public_base_url: str) -> str | None:
    if not url:
        return None
    base = public_base_url.rstrip("/") + "/"
    if url.startswith(base):
        return url[len(base):]
    return urlparse(url).path.lstrip("/") or None


def list_keys(client, bucket: str, prefix: str) -> list[str]:
    keys: list[str] = []
    token = None
    while True:
        params = {"Bucket": bucket, "Prefix": prefix}
        if token:
            params["ContinuationToken"] = token
        response = client.list_objects_v2(**params)
        keys.extend(item["Key"] for item in response.get("Contents", []))
        if not response.get("IsTruncated"):
            return keys
        token = response.get("NextContinuationToken")


def delete_r2_keys(client, bucket: str, keys: list[str]) -> None:
    for start in range(0, len(keys), 1000):
        batch = keys[start : start + 1000]
        client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": key} for key in batch], "Quiet": True},
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Xóa một truyện khỏi Cloudflare D1 + R2.")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--title", help="Tên truyện chính xác trên D1")
    selector.add_argument("--public-id", help="public_id, ví dụ new-15")
    parser.add_argument("--yes", action="store_true", help="Xóa thật; mặc định chỉ dry-run")
    args = parser.parse_args()
    load_dotenv()

    if args.title:
        books = d1_rows(
            "SELECT id, public_id, title, cover_url, chapter_count FROM books WHERE title = ?",
            [args.title],
        )
    else:
        books = d1_rows(
            "SELECT id, public_id, title, cover_url, chapter_count FROM books WHERE public_id = ?",
            [args.public_id],
        )

    if not books:
        print("❌ Không tìm thấy truyện trên D1.")
        return 1
    if len(books) > 1:
        print("❌ Có nhiều truyện trùng tiêu chí; hãy dùng --public-id.")
        return 1

    book = books[0]
    chapters = d1_rows(
        "SELECT content_path FROM chapters WHERE book_id = ? ORDER BY chapter_number",
        [book["id"]],
    )
    client, env = create_r2_client()
    chapter_keys = list_keys(client, env["R2_BUCKET"], f"chapters/{book['public_id']}/")
    cover_key = r2_key_from_url(book.get("cover_url", ""), env["R2_PUBLIC_BASE_URL"])
    keys = sorted(set(chapter_keys + ([cover_key] if cover_key else [])))

    print(f"📖 Truyện: {book['title']} ({book['public_id']})")
    print(f"📚 Chapter trong D1: {len(chapters)}")
    print(f"📦 Object sẽ xóa trên R2: {len(keys)}")
    if not args.yes:
        print("🧪 Dry-run: chưa xóa gì. Thêm --yes để xác nhận.")
        return 0

    delete_r2_keys(client, env["R2_BUCKET"], keys)
    d1_query("DELETE FROM chapters WHERE book_id = ?", [book["id"]])
    d1_query("DELETE FROM books WHERE id = ?", [book["id"]])
    print("✅ Đã xóa truyện khỏi D1 và các object liên quan khỏi R2.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
