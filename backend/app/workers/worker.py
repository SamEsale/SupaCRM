from __future__ import annotations

from redis import Redis
from rq import Worker

from app.core.config import settings
from app.workers.queue import get_queue


def main() -> None:
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    queue = get_queue()
    worker = Worker([queue], connection=redis, name=f"{settings.APP_NAME.lower().replace(' ', '-')}-worker")
    worker.work()


if __name__ == "__main__":
    main()
