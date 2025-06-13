import os
import sys

from rq import Worker

from app.config.redis_config import get_email_queue, get_pdf_queue, get_redis_connection

"""
def main():
    print(f"Starting RQ Worker")

    try:
        redis_conn = get_redis_connection()

        pdf_queue = get_pdf_queue()
        email_queue = get_email_queue()

        print(f"Listening to PDF queue")
        print(f"Listening to Email queue")

        worker = Worker([pdf_queue, email_queue], connection=redis_conn)

        print(f"Worker is ready and listening")
        print(f"Processing jobs...")

        worker.work()

    except KeyboardInterrupt:
        print(f"Interrupted by user")
    except Exception as e:
        print(f"Worker error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
"""
