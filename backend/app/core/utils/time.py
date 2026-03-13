"""Time utilities placeholder"""

from datetime import datetime


def now_iso():
    return datetime.utcnow().isoformat() + "Z"
