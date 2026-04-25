#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / ".env.supa"


def load_env_value(key: str) -> str | None:
    if not ENV_FILE.exists():
        return None

    for raw in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        env_key, value = line.split("=", 1)
        if env_key.strip() == key:
            return value.strip().strip('"').strip("'")
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap a local tenant + first admin through the real internal bootstrap API.",
    )
    parser.add_argument(
        "--base-url",
        default=load_env_value("APP_BASE_URL") or "http://127.0.0.1:8000",
        help="Backend base URL. Defaults to APP_BASE_URL from .env.supa or http://127.0.0.1:8000.",
    )
    parser.add_argument("--tenant-id", required=True, help="Tenant identifier")
    parser.add_argument("--tenant-name", required=True, help="Tenant display name")
    parser.add_argument("--admin-email", required=True, help="First admin email")
    parser.add_argument("--admin-full-name", default="SupaCRM Admin", help="First admin full name")
    parser.add_argument("--admin-password", required=True, help="First admin password")
    parser.add_argument(
        "--bootstrap-key",
        default=load_env_value("BOOTSTRAP_API_KEY"),
        help="Internal bootstrap key. Defaults to BOOTSTRAP_API_KEY from .env.supa.",
    )
    return parser.parse_args()


def request_json(*, url: str, method: str, headers: dict[str, str] | None = None, payload: dict | None = None) -> dict:
    request = Request(
        url=url,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers=headers or {},
        method=method,
    )
    with urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def main() -> int:
    args = parse_args()

    if not args.bootstrap_key:
        print("ERROR: missing bootstrap key. Set BOOTSTRAP_API_KEY in .env.supa or pass --bootstrap-key.", file=sys.stderr)
        return 1

    payload = {
        "tenant_id": args.tenant_id,
        "tenant_name": args.tenant_name,
        "admin_email": args.admin_email,
        "admin_full_name": args.admin_full_name,
        "admin_password": args.admin_password,
    }

    try:
        request_json(url=f"{args.base_url.rstrip('/')}/health", method="GET")
        request_json(
            url=f"{args.base_url.rstrip('/')}/internal/bootstrap/ping",
            method="GET",
            headers={"X-Bootstrap-Key": args.bootstrap_key},
        )
        body = request_json(
            url=f"{args.base_url.rstrip('/')}/internal/bootstrap/tenants/bootstrap",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Bootstrap-Key": args.bootstrap_key,
            },
            payload=payload,
        )
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"ERROR: bootstrap request failed with HTTP {exc.code}: {detail}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"ERROR: could not reach backend bootstrap endpoint: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(body, indent=2))
    print()
    print("Next steps:")
    print("1. Open http://127.0.0.1:3000/login")
    print(f"2. Sign in as {args.admin_email}")
    print(f"3. Verify onboarding at http://127.0.0.1:3000/onboarding")
    print(f"4. Run bash scripts/dev/smoke_local_launch.sh with SMOKE_EMAIL={args.admin_email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
