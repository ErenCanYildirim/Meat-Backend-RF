import os

import redis
from rq import Queue, Worker
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


def retry_failed_job(job_id: str, max_retries: int = 3) -> bool:
    try:
        redis_conn = get_redis_connection()
        job = Job.fetch(job_id, connection=redis_conn)

        retry_count = job.meta.get("retry_count", 0)

        if retry_count >= max_retries:
            dlq = get_dead_letter_queue()
            dlq.enqueue(
                "dead_letter_handler",
                job_data={
                    "original_func": job.func_name,
                    "args": job.args,
                    "kwargs": job.kwargs,
                    "failure_reason": str(job.exc_info),
                    "retry_count": retry_count,
                },
                job_timeout=60,
            )
            return False

        job.meta["retry_count"] = retry_count + 1
        job.save_meta()

        delay = 2**retry_count * 60

        if "pdf" in job.func_name:
            queue = get_pdf_queue()
        else:
            queue = get_email_queue()

        queue.enqueue_in(
            delay,
            job.func,
            *job.args,
            **job.kwargs,
            job_timeout=job.timeout,
            job_id=f"{job_id}_retry_{retry_count+1}",
        )

        return True
    except Exception as e:
        print(f"Error retrying job: {job_id}: {e}")
        return False


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
