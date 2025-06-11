import sys
import os
from rq import Worker
from app.config.redis_config import get_redis_connection, get_pdf_queue


def main():
    print(f"Starting PDF Worker")
    try:
        redis_conn = get_redis_connection()
        pdf_queue = get_pdf_queue()
        print(f"Listening to PDF queue only")

        worker = Worker([pdf_queue], connection=redis_conn)
        print(f"PDF worker is ready and listening")
        worker.work()
    except KeyboardInterrupt:
        print(f"PDF Worker interrupted by user")
    except Exception as e:
        print(f"PDF Worker error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
