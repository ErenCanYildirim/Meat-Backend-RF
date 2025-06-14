import os
import sys

from rq import Worker
from rq.job import Job

from app.config.logging_config import get_logger, setup_logging
from app.config.redis_config import (get_email_queue, get_redis_connection,
                                     retry_failed_job)

environment = os.getenv("ENVIRONMENT", "development")
setup_logging(environment)
logger = get_logger(__name__)


def handle_job_failure(job: Job, *exc_info):
    print(f"Job {job.id} failed: {exc_info}")
    retry_failed_job(job.id)


def main():
    print(f"Starting Email Worker")
    try:
        redis_conn = get_redis_connection()
        email_queue = get_email_queue()
        print(f"Listening to Email queue only")

        worker = Worker([email_queue], connection=redis_conn)
        worker.push_exc_handler(handle_job_failure)

        print(f"Email Worker is ready and listening")
        worker.work()
    except KeyboardInterrupt:
        print(f"Email Worker interrupted by user")
    except Exception as e:
        print(f"Email Worker error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
