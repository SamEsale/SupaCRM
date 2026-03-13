from pathlib import Path

def get_repo_root() -> Path:
    """
    Resolve SupaCRM repo root.
    Assumes this file lives at: backend/app/core/paths.py
    """
    return Path(__file__).resolve().parents[3]
