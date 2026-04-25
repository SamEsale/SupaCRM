import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
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


def main() -> int:
    env_path = find_upwards(".env.supa", Path.cwd())
    if not env_path:
        print("ERROR: Could not find .env.supa by searching upwards from cwd.")
        return 2
    load_dotenv(env_path, override=False)

    dsn = os.getenv("DATABASE_URL_SYNC") or os.getenv("DATABASE_URL")
    if not dsn:
        print("ERROR: DATABASE_URL_SYNC (or DATABASE_URL) not set")
        return 2
    dsn = dsn.replace("postgresql+psycopg://", "postgresql://")

    verify_email = os.getenv("VERIFY_ADMIN_EMAIL")  # optional

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("select count(1) as n from public.user_credentials")
            print("user_credentials rows =", cur.fetchone()["n"])

            print("\n== Latest user_credentials ==")
            cur.execute(
                """
                select
                    uc.user_id,
                    uc.is_password_set,
                    length(uc.password_hash) as hash_len,
                    uc.created_at,
                    uc.updated_at
                from public.user_credentials uc
                order by uc.created_at desc
                limit 10
                """
            )
            rows = cur.fetchall()
            if not rows:
                print("(none)")
            else:
                for r in rows:
                    print(
                        f"- user_id={r['user_id']} "
                        f"is_password_set={r['is_password_set']} "
                        f"hash_len={r['hash_len']} "
                        f"created_at={r['created_at']} "
                        f"updated_at={r['updated_at']}"
                    )

            if verify_email:
                print(f"\n== Check by email: {verify_email} ==")
                cur.execute(
                    """
                    select
                        u.id as user_id,
                        u.email,
                        uc.is_password_set,
                        length(uc.password_hash) as hash_len
                    from public.users u
                    left join public.user_credentials uc on uc.user_id = u.id
                    where u.email = %s
                    """,
                    (verify_email,),
                )
                row = cur.fetchone()
                if not row:
                    print("No such user email found.")
                    return 3

                print("user_id:", row["user_id"])
                print("email:", row["email"])
                print("is_password_set:", row["is_password_set"])
                print("hash_len:", row["hash_len"])

                if row["hash_len"] is None:
                    print("❌ No credentials row for this user.")
                    return 4
                if row["hash_len"] <= 0:
                    print("❌ Credentials row exists but password_hash is empty.")
                    return 5

                print("✅ Credentials exist and password_hash is non-empty (hash not printed).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
