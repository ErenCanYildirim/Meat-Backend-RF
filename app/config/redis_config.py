import os
import redis
from rq import Queue

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_conn = redis.from_url(redis_url)

pdf_queue = Queue("pdf_generation", connection=redis_conn)
email_queue = Queue("email_sending", connection=redis_conn)


def get_redis_connection():
    return redis_conn


def get_pdf_queue():
    return pdf_queue


def get_email_queue():
    return email_queue
