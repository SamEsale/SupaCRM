import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


def find_upwards(filename: str, start: Path):
    cur = start.resolve()
    while True:
        cand = cur / filename
        if cand.exists():
            return cand
        if cur.parent == cur:
            return None
        cur = cur.parent


env_path = find_upwards(".env.supa", Path.cwd())
if env_path:
    load_dotenv(env_path, override=False)

dsn = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL")
if not dsn:
    raise SystemExit("ERROR: DATABASE_URL_SYNC (or DATABASE_URL) not set")
dsn = dsn.replace("postgresql+psycopg://", "postgresql://")

with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute("select count(1) from public.user_credentials")
        print("user_credentials rows =", cur.fetchone()[0])
