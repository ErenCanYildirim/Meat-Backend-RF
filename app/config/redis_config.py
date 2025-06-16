import os

import redis
from rq import Queue, Retry, Worker
from rq.job import Job

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_conn = redis.from_url(redis_url)

pdf_queue = Queue("pdf_generation", connection=redis_conn)
email_queue = Queue("email_sending", connection=redis_conn)
dead_letter_queue = Queue("dead_letter", connection=redis_conn)


def get_redis_connection():
    return redis_conn


def get_pdf_queue():
    return pdf_queue


def get_email_queue():
    return email_queue


def get_dead_letter_queue():
    return dead_letter_queue


def move_to_dead_letter_queue(job, exc_string):
    try:
        dlq = get_dead_letter_queue()
        dlq.enqueue(
            "dead_letter_handler",
            job_data={
                "original_func": job.func_name,
                "args": job.args,
                "kwargs": job.kwargs,
                "failure_reason": exc_string,
                "original_job_id": job.id,
            },
            timeout=60,
        )
        print(f"Job {job.id} moved to dead letter queue after max retries.")
    except Exception as e:
        print(f"Error moving job to dead letter queue: {e}")


def get_queue_stats():
    return {
        "pdf_queue_length": len(pdf_queue),
        "email_queue_length": len(email_queue),
        "dead_letter_queue": len(dead_letter_queue),
        "pdf_queue_failed": pdf_queue.failed_job_registry.count,
        "email_queue_failed": email_queue.failed_job_registry.count,
    }


def get_worker_stats():
    workers = Worker.all(connection=redis_conn)
    return {
        "total_workers": len(workers),
        "active_workers": len([w for w in workers if w.get_state() == "busy"]),
        "idle_workers": len([w for w in workers if w.get_state() == "idle"]),
    }
