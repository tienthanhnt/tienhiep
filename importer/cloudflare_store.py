import json
import os
import sys
import urllib.error
import urllib.request

import boto3
from botocore.config import Config


D1_REQUIRED_ENV = (
    "CLOUDFLARE_ACCOUNT_ID",
    "D1_DATABASE_ID",
    "CLOUDFLARE_API_TOKEN",
)
R2_REQUIRED_ENV = (
    "R2_BUCKET",
    "R2_ENDPOINT",
    "R2_PUBLIC_BASE_URL",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
)


def require_env(keys: tuple[str, ...]) -> dict[str, str]:
    missing = [key for key in keys if not os.environ.get(key)]
    if missing:
        print("❌ Thiếu biến môi trường trong importer/.env:")
        for key in missing:
            print(f"   - {key}")
        sys.exit(1)

    values = {key: os.environ[key].strip() for key in keys}
    if "R2_PUBLIC_BASE_URL" in values:
        values["R2_PUBLIC_BASE_URL"] = values["R2_PUBLIC_BASE_URL"].rstrip("/")
    return values


def d1_query(sql: str, params: list[object] | None = None) -> dict:
    return d1_request({"sql": sql, "params": params or []})


def d1_batch(batch: list[dict]) -> dict:
    return d1_request({"batch": batch})


def d1_request(payload_object: dict) -> dict:
    env = require_env(D1_REQUIRED_ENV)
    endpoint = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{env['CLOUDFLARE_ACCOUNT_ID']}/d1/database/{env['D1_DATABASE_ID']}/query"
    )
    payload = json.dumps(payload_object, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {env['CLOUDFLARE_API_TOKEN']}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Cloudflare D1 HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Không kết nối được Cloudflare D1 API: {exc}") from exc

    data = json.loads(body)
    if not data.get("success"):
        raise RuntimeError(f"Cloudflare D1 trả lỗi: {json.dumps(data, ensure_ascii=False)}")

    query_results = data.get("result") or []
    failed_result = next((result for result in query_results if not result.get("success", False)), None)
    if failed_result:
        raise RuntimeError(f"D1 query lỗi: {json.dumps(failed_result, ensure_ascii=False)}")

    return data


def d1_rows(sql: str, params: list[object] | None = None) -> list[dict]:
    data = d1_query(sql, params)
    return ((data.get("result") or [{}])[0].get("results") or [])


def create_r2_client():
    env = require_env(R2_REQUIRED_ENV)
    client = boto3.client(
        "s3",
        endpoint_url=env["R2_ENDPOINT"],
        aws_access_key_id=env["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )
    return client, env


def upload_r2_object(
    key: str,
    body: bytes,
    content_type: str,
    cache_control: str = "86400",
) -> str:
    client, env = create_r2_client()
    client.put_object(
        Bucket=env["R2_BUCKET"],
        Key=key,
        Body=body,
        ContentType=content_type,
        CacheControl=f"public, max-age={cache_control}",
    )
    return f"{env['R2_PUBLIC_BASE_URL']}/{key}"
