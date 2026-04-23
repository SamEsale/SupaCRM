#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_SCRIPT = REPO_ROOT / "backend" / "scripts" / "create_tenant.py"
PYTHON_BIN = REPO_ROOT / "backend" / ".venv313" / "bin" / "python"


def main() -> int:
    print("NOTE: this is a low-level DB helper. Preferred operator path: scripts/dev/bootstrap_local_operator.py", file=sys.stderr)
    command = [str(PYTHON_BIN), str(BACKEND_SCRIPT), *sys.argv[1:]]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
