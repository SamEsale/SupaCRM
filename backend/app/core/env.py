import os
from pathlib import Path

from app.core.paths import get_repo_root

_ENV_LOADED = False


def load_env_supa() -> None:
    """
    Load .env.supa from repo root into os.environ (idempotent).

    Behavior:
    - Does NOT overwrite existing env vars by default (prod-safe)
    - BUT will overwrite JWT secrets if:
        * missing, OR
        * placeholder value, OR
        * too short (<64 chars)
    """
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    env_path: Path = (get_repo_root() / ".env.supa").resolve()
    if not env_path.exists():
        return

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        existing = os.getenv(key)

        # Default: don't clobber real env vars (prod-safe)
        should_override = False

        if not existing:
            should_override = True
        elif existing.startswith("REPLACE_WITH_REAL_"):
            should_override = True
        elif key in ("JWT_SECRET", "REFRESH_TOKEN_SECRET") and len(existing) < 64:
            should_override = True

        if should_override:
            os.environ[key] = value

    _ENV_LOADED = True
