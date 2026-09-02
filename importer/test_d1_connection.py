#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

from dotenv import load_dotenv


load_dotenv()


REQUIRED_ENV = (
    "CLOUDFLARE_ACCOUNT_ID",
    "D1_DATABASE_ID",
    "CLOUDFLARE_API_TOKEN",
)


def require_env() -> dict[str, str]:
    missing = [key for key in REQUIRED_ENV if not os.environ.get(key)]
    if missing:
        print("❌ Thiếu biến môi trường D1 trong importer/.env:")
        for key in missing:
            print(f"   - {key}")
        sys.exit(1)

    return {key: os.environ[key].strip() for key in REQUIRED_ENV}


def mask(value: str) -> str:
    if len(value) <= 10:
        return "***"
    return f"{value[:6]}...{value[-4:]}"


def d1_query(env: dict[str, str], sql: str, params: list[str] | None = None) -> dict:
    endpoint = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{env['CLOUDFLARE_ACCOUNT_ID']}/d1/database/{env['D1_DATABASE_ID']}/query"
    )
    payload = json.dumps({"sql": sql, "params": params or []}).encode("utf-8")
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
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Cloudflare API HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Không kết nối được Cloudflare API: {exc}") from exc

    result = json.loads(body)
    if not result.get("success"):
        raise RuntimeError(f"Cloudflare API trả lỗi: {json.dumps(result, ensure_ascii=False)}")

    query_results = result.get("result") or []
    if query_results and not query_results[0].get("success", False):
        raise RuntimeError(f"D1 query lỗi: {json.dumps(query_results[0], ensure_ascii=False)}")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Test kết nối Cloudflare D1 bằng query nhỏ.")
    parser.add_argument(
        "--keep-table",
        action="store_true",
        help="Giữ bảng _d1_connection_test sau khi test.",
    )
    args = parser.parse_args()

    env = require_env()
    marker = datetime.now(timezone.utc).strftime("test-%Y%m%d-%H%M%S")

    try:
        print(f"🔎 Account ID : {mask(env['CLOUDFLARE_ACCOUNT_ID'])}")
        print(f"🔎 Database ID: {mask(env['D1_DATABASE_ID'])}")

        d1_query(
            env,
            """
            CREATE TABLE IF NOT EXISTS _d1_connection_test (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              marker TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
        )
        print("✅ CREATE TABLE OK")

        d1_query(env, "INSERT INTO _d1_connection_test (marker) VALUES (?)", [marker])
        print("✅ INSERT OK")

        selected = d1_query(
            env,
            "SELECT id, marker, created_at FROM _d1_connection_test WHERE marker = ? LIMIT 1",
            [marker],
        )
        rows = ((selected.get("result") or [{}])[0].get("results") or [])
        if not rows:
            raise RuntimeError("SELECT không trả lại row vừa insert.")

        print(f"✅ SELECT OK: marker={rows[0].get('marker')}")

        if args.keep_table:
            d1_query(env, "DELETE FROM _d1_connection_test WHERE marker = ?", [marker])
            print("🧹 Đã xóa row test, giữ bảng test vì có --keep-table.")
        else:
            d1_query(env, "DROP TABLE IF EXISTS _d1_connection_test")
            print("🧹 Đã xóa bảng test.")

        print("🎉 D1 connection OK.")
        return 0
    except Exception as exc:
        print(f"❌ D1 test thất bại: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
