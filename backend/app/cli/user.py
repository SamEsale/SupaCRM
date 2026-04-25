import asyncio
import uuid
from typing import Optional

import typer
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError
from sqlalchemy import text

from app.db import async_session_factory

app = typer.Typer(no_args_is_help=True, help="User administration utilities")
ph = PasswordHasher()


def _require_exactly_one_identifier(email: Optional[str], user_id: Optional[str]) -> None:
    if (email is None and user_id is None) or (email is not None and user_id is not None):
        raise typer.BadParameter("Provide exactly one of --email or --user-id")


def _validate_uuid(user_id: str) -> None:
    try:
        uuid.UUID(user_id)
    except ValueError:
        raise typer.BadParameter("--user-id must be a valid UUID")


async def _resolve_user_id(session, email: Optional[str], user_id: Optional[str]) -> str:
    """
    Resolve and validate user_id from either email or user_id.
    Ensures the user exists.
    """
    if user_id is not None:
        _validate_uuid(user_id)
        res = await session.execute(
            text(
                """
                select 1
                from public.users
                where id = CAST(:user_id AS varchar)
                """
            ),
            {"user_id": user_id},
        )
        if res.scalar_one_or_none() is None:
            raise typer.Exit(code=2)
        return user_id

    # email path
    res = await session.execute(
        text(
            """
            select id
            from public.users
            where email = CAST(:email AS varchar)
            """
        ),
        {"email": email},
    )
    uid = res.scalar_one_or_none()
    if not uid:
        raise typer.Exit(code=2)
    return str(uid)


@app.command("set-password")
def set_password(
    password: str = typer.Option(..., "--password", help="New password (plaintext, will be hashed)"),
    email: Optional[str] = typer.Option(None, "--email", help="User email (preferred identifier)"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="User UUID (alternative identifier)"),
) -> None:
    """
    Set (or reset) a user's password by email or user_id.
    Stores argon2 hash in public.user_credentials (UPSERT).
    """
    _require_exactly_one_identifier(email, user_id)
    asyncio.run(_set_password_async(email=email, user_id=user_id, password=password))


async def _set_password_async(email: Optional[str], user_id: Optional[str], password: str) -> None:
    password_hash = ph.hash(password)

    async with async_session_factory() as session:
        async with session.begin():
            uid = await _resolve_user_id(session, email=email, user_id=user_id)

            await session.execute(
                text(
                    """
                    insert into public.user_credentials (user_id, password_hash, is_password_set)
                    values (CAST(:user_id AS varchar), CAST(:password_hash AS text), true)
                    on conflict (user_id) do update
                      set password_hash = excluded.password_hash,
                          is_password_set = true,
                          updated_at = now()
                    """
                ),
                {"user_id": uid, "password_hash": password_hash},
            )

    if email:
        typer.echo(f"✅ Password set for user email={email} (argon2 hash stored)")
    else:
        typer.echo(f"✅ Password set for user_id={user_id} (argon2 hash stored)")


@app.command("verify-password")
def verify_password(
    password: str = typer.Option(..., "--password", help="Password to verify against stored hash"),
    email: Optional[str] = typer.Option(None, "--email", help="User email (preferred identifier)"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="User UUID (alternative identifier)"),
) -> None:
    """
    Verify a password against the stored argon2 hash for a user.
    Prints PASS/FAIL only (never prints the hash).
    """
    _require_exactly_one_identifier(email, user_id)
    asyncio.run(_verify_password_async(email=email, user_id=user_id, password=password))


async def _verify_password_async(email: Optional[str], user_id: Optional[str], password: str) -> None:
    async with async_session_factory() as session:
        uid = await _resolve_user_id(session, email=email, user_id=user_id)

        res = await session.execute(
            text(
                """
                select password_hash, is_password_set
                from public.user_credentials
                where user_id = CAST(:user_id AS varchar)
                """
            ),
            {"user_id": uid},
        )
        row = res.mappings().first()

        if not row:
            typer.echo("FAIL: No credentials row found for this user.")
            raise typer.Exit(code=3)

        if not row["is_password_set"]:
            typer.echo("FAIL: Credentials row exists but is_password_set=false.")
            raise typer.Exit(code=4)

        password_hash = row["password_hash"]

        try:
            ph.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHash):
            typer.echo("FAIL: password does NOT match stored hash.")
            raise typer.Exit(code=5)
        except Exception:
            # Any unexpected argon2/cffi error: treat as failure but keep a distinct code.
            typer.echo("FAIL: could not verify password (unexpected error).")
            raise typer.Exit(code=6)

        # Optional: rehash if parameters changed
        try:
            if ph.check_needs_rehash(password_hash):
                new_hash = ph.hash(password)
                async with session.begin():
                    await session.execute(
                        text(
                            """
                            update public.user_credentials
                            set password_hash = CAST(:password_hash AS text),
                                is_password_set = true,
                                updated_at = now()
                            where user_id = CAST(:user_id AS varchar)
                            """
                        ),
                        {"user_id": uid, "password_hash": new_hash},
                    )
        except Exception:
            # Rehash failure shouldn't block auth verification success.
            pass

        typer.echo("PASS: password matches stored hash.")
        raise typer.Exit(code=0)


@app.command("ensure-credentials")
def ensure_credentials(
    email: Optional[str] = typer.Option(None, "--email", help="User email (preferred identifier)"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="User UUID (alternative identifier)"),
    set_false: bool = typer.Option(
        False,
        "--set-false",
        help="If creating a placeholder row, set is_password_set=false (recommended)",
    ),
) -> None:
    """
    Ensure a user has a row in public.user_credentials.
    Does NOT set a usable password; it creates a placeholder hash and (by default) is_password_set=false.
    """
    _require_exactly_one_identifier(email, user_id)
    asyncio.run(_ensure_credentials_async(email=email, user_id=user_id, set_false=set_false))


async def _ensure_credentials_async(email: Optional[str], user_id: Optional[str], set_false: bool) -> None:
    # Placeholder hash (never used for login because is_password_set will be false by default).
    placeholder_hash = ph.hash(str(uuid.uuid4()))

    async with async_session_factory() as session:
        async with session.begin():
            uid = await _resolve_user_id(session, email=email, user_id=user_id)

            await session.execute(
                text(
                    """
                    insert into public.user_credentials (user_id, password_hash, is_password_set)
                    values (CAST(:user_id AS varchar), CAST(:password_hash AS text), :is_password_set)
                    on conflict (user_id) do nothing
                    """
                ),
                {
                    "user_id": uid,
                    "password_hash": placeholder_hash,
                    "is_password_set": (False if set_false else True),
                },
            )

    if email:
        typer.echo(f"✅ Ensured credentials row exists for email={email}")
    else:
        typer.echo(f"✅ Ensured credentials row exists for user_id={user_id}")


@app.command("disable-password")
def disable_password(
    email: Optional[str] = typer.Option(None, "--email", help="User email (preferred identifier)"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="User UUID (alternative identifier)"),
) -> None:
    """
    Disable password authentication for a user:
      - set is_password_set=false
      - replace password_hash with a random value (so previous hash cannot be used even if a bug ignores the flag)
    """
    _require_exactly_one_identifier(email, user_id)
    asyncio.run(_disable_password_async(email=email, user_id=user_id))


async def _disable_password_async(email: Optional[str], user_id: Optional[str]) -> None:
    replacement_hash = ph.hash(str(uuid.uuid4()))

    async with async_session_factory() as session:
        async with session.begin():
            uid = await _resolve_user_id(session, email=email, user_id=user_id)

            res = await session.execute(
                text(
                    """
                    update public.user_credentials
                    set is_password_set = false,
                        password_hash = CAST(:password_hash AS text),
                        updated_at = now()
                    where user_id = CAST(:user_id AS varchar)
                    """
                ),
                {"user_id": uid, "password_hash": replacement_hash},
            )

            if res.rowcount == 0:
                # No credentials row: create disabled row
                await session.execute(
                    text(
                        """
                        insert into public.user_credentials (user_id, password_hash, is_password_set)
                        values (CAST(:user_id AS varchar), CAST(:password_hash AS text), false)
                        on conflict (user_id) do update
                          set is_password_set = false,
                              password_hash = excluded.password_hash,
                              updated_at = now()
                        """
                    ),
                    {"user_id": uid, "password_hash": replacement_hash},
                )

    if email:
        typer.echo(f"✅ Disabled password for email={email}")
    else:
        typer.echo(f"✅ Disabled password for user_id={user_id}")
