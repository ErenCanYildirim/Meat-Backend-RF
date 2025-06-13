import os
import sys

from rq import Worker

from app.config.redis_config import get_email_queue, get_redis_connection


def main():
    print(f"Starting Email Worker")
    try:
        redis_conn = get_redis_connection()
        email_queue = get_email_queue()
        print(f"Listening to Email queue only")

        worker = Worker([email_queue], connection=redis_conn)
        print(f"Email Worker is ready and listening")
        worker.work()
    except KeyboardInterrupt:
        print(f"Email Worker interrupted by user")
    except Exception as e:
        print(f"Email Worker error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
