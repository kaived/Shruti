import logging

from redis import Redis
from rq import Worker

from core.config import Settings
from core.database import Database


def main():
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    db = Database(settings)
    db.initialize()
    db.engine.dispose()
    connection = Redis.from_url(settings.redis_url)
    Worker(["shruti"], connection=connection).work(burst=settings.worker_burst)


if __name__ == "__main__":
    main()
