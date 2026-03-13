import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


def find_upwards(filename: str, start: Path) -> Path | None:
    cur = start.resolve()
    while True:
        candidate = cur / filename
        if candidate.exists():
            return candidate
        if cur.parent == cur:
            return None
        cur = cur.parent


def main() -> int:
    env_path = find_upwards(".env.supa", Path.cwd())
    if env_path:
        load_dotenv(env_path, override=False)

    dsn = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("ERROR: DATABASE_URL_SYNC (or DATABASE_URL) not set")

    dsn = dsn.replace("postgresql+psycopg://", "postgresql://")

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("select to_regclass('public.user_credentials')")
            print("user_credentials =", cur.fetchone()[0])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
