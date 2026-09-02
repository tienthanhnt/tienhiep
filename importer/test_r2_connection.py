#!/usr/bin/env python3
import argparse
import os
import sys
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv


load_dotenv()


REQUIRED_ENV = (
    "R2_BUCKET",
    "R2_ENDPOINT",
    "R2_PUBLIC_BASE_URL",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
)


def require_env() -> dict[str, str]:
    missing = [key for key in REQUIRED_ENV if not os.environ.get(key)]
    if missing:
        print("❌ Thiếu biến môi trường R2 trong importer/.env:")
        for key in missing:
            print(f"   - {key}")
        sys.exit(1)

    return {key: os.environ[key].strip().rstrip("/") for key in REQUIRED_ENV}


def create_client(env: dict[str, str]):
    return boto3.client(
        "s3",
        endpoint_url=env["R2_ENDPOINT"],
        aws_access_key_id=env["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Test kết nối Cloudflare R2 bằng file nhỏ.")
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Giữ file test trên R2 thay vì xóa sau khi kiểm tra.",
    )
    args = parser.parse_args()

    env = require_env()
    client = create_client(env)
    key = f"_r2_test/{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
    body = "Tien Hiep Lau R2 connection test\n".encode("utf-8")

    try:
        print(f"🔎 Bucket: {env['R2_BUCKET']}")
        print(f"⬆️  Upload test object: {key}")
        client.put_object(
            Bucket=env["R2_BUCKET"],
            Key=key,
            Body=body,
            ContentType="text/plain; charset=utf-8",
            CacheControl="no-store",
        )

        head = client.head_object(Bucket=env["R2_BUCKET"], Key=key)
        size = head.get("ContentLength", 0)
        public_url = f"{env['R2_PUBLIC_BASE_URL']}/{key}"

        print(f"✅ Upload OK. Size: {size} bytes")
        print(f"🌐 Public URL: {public_url}")

        if args.keep:
            print("ℹ️  Đã giữ file test vì có --keep.")
        else:
            client.delete_object(Bucket=env["R2_BUCKET"], Key=key)
            print("🧹 Đã xóa file test khỏi R2.")

        return 0
    except (BotoCoreError, ClientError) as exc:
        print(f"❌ R2 test thất bại: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
