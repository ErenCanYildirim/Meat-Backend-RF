import os
import sys

from rq import Worker
from rq.job import Job

from app.config.logging_config import get_logger, setup_logging
from app.config.redis_config import get_pdf_queue, get_redis_connection

environment = os.getenv("ENVIRONMENT", "development")
setup_logging(environment)
logger = get_logger(__name__)


def handle_job_failure(job: Job, *exc_info):
    print(f"Job {job.id} failed: {exc_info}")
    retry_failed_job(job.id)


def main():
    print(f"Starting PDF Worker")
    try:
        redis_conn = get_redis_connection()
        pdf_queue = get_pdf_queue()
        print(f"Listening to PDF queue only")

        worker = Worker([pdf_queue], connection=redis_conn)
        worker.push_exc_handler(handle_job_failure)

        print(f"PDF worker is ready and listening")
        worker.work()
    except KeyboardInterrupt:
        print(f"PDF Worker interrupted by user")
    except Exception as e:
        print(f"PDF Worker error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
