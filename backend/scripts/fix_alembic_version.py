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
        print("ERROR: DATABASE_URL_SYNC (or DATABASE_URL) not set")
        return 2
    dsn = dsn.replace("postgresql+psycopg://", "postgresql://")

    target = os.getenv("TARGET_REVISION", "3ff6222d94c7")

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("select version_num from alembic_version")
            before = cur.fetchone()[0]
            print("Before:", before)

            cur.execute("update alembic_version set version_num = %s", (target,))
            conn.commit()

            cur.execute("select version_num from alembic_version")
            after = cur.fetchone()[0]
            print("After: ", after)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
