import os
import random
import sys
import time
from typing import Any, Dict

from rq import Retry

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)

sys.path.insert(0, grandparent_dir)


from app.config.redis_config import (get_dead_letter_queue, get_email_queue,
                                     get_pdf_queue, get_queue_stats,
                                     get_worker_stats)
from app.tests.test_dlq import print_queue_status
from app.tests.test_tasks import (create_test_order_data, dead_letter_handler,
                                  generate_pdf_task_with_failures,
                                  send_email_task_with_failures)


def inspect_dead_letter_queue():

    print("DETAILED DEAD LETTER QUEUE INSPECTION")
    print("=" * 60)

    try:
        dlq = get_dead_letter_queue()
        jobs = dlq.jobs

        print(f"Total jobs in DLQ: {len(jobs)}")

        for i, job in enumerate(jobs):
            print(f"\n--- JOB {i+1} ---")
            print(f"ID: {job.id}")
            print(f"Function: {job.func_name}")
            print(f"Status: {job.get_status()}")
            print(f"Created: {job.created_at}")
            print(f"Enqueued: {job.enqueued_at}")
            print(f"Started: {job.started_at}")
            print(f"Ended: {job.ended_at}")

            if hasattr(job, "exc_info") and job.exc_info:
                print(f"Exception: {str(job.exc_info)[:200]}...")

            try:
                if job.args:
                    print(f"Args: {str(job.args)[:100]}...")
                if job.kwargs:
                    print(f"Kwargs: {str(job.kwargs)[:100]}...")
            except:
                print("Could not access job arguments")

            if job.func_name == "app.tests.test_tasks.dead_letter_handler":
                try:
                    if job.args and len(job.args) > 0:
                        job_data = job.args[0]
                        if isinstance(job_data, dict):
                            print(
                                f"Original function: {job_data.get('original_func', 'Unknown')}"
                            )
                            print(
                                f"Original job ID: {job_data.get('original_job_id', 'Unknown')}"
                            )
                            print(
                                f"Failure reason: {job_data.get('failure_reason', 'Unknown')}"
                            )
                except Exception as e:
                    print(f"Could not parse dead letter handler data: {e}")

    except Exception as e:
        print(f"Error inspecting DLQ: {e}")
        import traceback

        traceback.print_exc()


def check_job_history():
    print("\nRECENT JOB HISTORY")
    print("=" * 60)

    try:
        pdf_queue = get_pdf_queue()
        email_queue = get_email_queue()

        print("PDF Queue Failed Jobs:")
        failed_pdf = pdf_queue.failed_job_registry.get_job_ids()
        for job_id in failed_pdf[:5]:
            try:
                job = pdf_queue.failed_job_registry.requeue(job_id)
                print(f"  - {job_id}: {job.func_name if job else 'Could not load'}")
            except:
                print(f"  - {job_id}: Could not load job details")

        print(f"Email Queue Failed Jobs:")
        failed_email = email_queue.failed_job_registry.get_job_ids()
        for job_id in failed_email[:5]:
            try:
                job = email_queue.failed_job_registry.requeue(job_id)
                print(f"  - {job_id}: {job.func_name if job else 'Could not load'}")
            except:
                print(f"  - {job_id}: Could not load job details")

    except Exception as e:
        print(f"Error checking job history: {e}")


def test_dead_letter_handler_directly():
    print("\nTESTING DEAD LETTER HANDLER DIRECTLY")
    print("=" * 60)

    try:
        sample_job_data = {
            "original_func": "generate_pdf_task_with_failures",
            "args": [{"order_id": "test-123", "customer_email": "test@example.com"}],
            "kwargs": {"failure_mode": "test"},
            "failure_reason": "Test failure for diagnostic",
            "original_job_id": "diagnostic-test-456",
        }

        print("Sample job data created:")
        print(f"  Original function: {sample_job_data['original_func']}")
        print(f"  Original job ID: {sample_job_data['original_job_id']}")
        print(f"  Failure reason: {sample_job_data['failure_reason']}")

        try:
            from app.tests.test_tasks import dead_letter_handler

            print("\nCalling dead_letter_handler directly...")
            result = dead_letter_handler(job_data=sample_job_data)
            print(f"Direct call successful: {result}")
        except Exception as e:
            print(f"Direct call failed: {e}")
            import traceback

            traceback.print_exc()

        print("\nEnqueueing to dead letter queue...")
        dlq = get_dead_letter_queue()
        job = dlq.enqueue(dead_letter_handler, job_data=sample_job_data, timeout=60)
        print(f"Enqueued as job {job.id}")

        import time

        time.sleep(5)
        job.refresh()
        print(f"Job status after 5 seconds: {job.get_status()}")

    except Exception as e:
        print(f"Error testing dead letter handler: {e}")
        import traceback

        traceback.print_exc()


def main():
    print("DEAD LETTER QUEUE DIAGNOSTIC")
    print("=" * 60)

    print_queue_status()

    inspect_dead_letter_queue()

    check_job_history()

    test_dead_letter_handler_directly()

    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
