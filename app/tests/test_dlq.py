import time
import sys
import os
from rq import Retry

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)

sys.path.insert(0, grandparent_dir)


from app.config.redis_config import (
    get_pdf_queue, 
    get_email_queue, 
    get_dead_letter_queue,
    get_queue_stats,
    get_worker_stats
)
from app.tests.test_tasks import (  
    generate_pdf_task_with_failures,
    send_email_task_with_failures,
    dead_letter_handler,
    create_test_order_data
)



def print_queue_status():
    """Print current status of all queues"""
    print("\n" + "="*60)
    print("QUEUE STATUS")
    print("="*60)
    
    try:
        stats = get_queue_stats()
        worker_stats = get_worker_stats()
        
        print(f"PDF Queue Length: {stats.get('pdf_queue_length', 'N/A')}")
        print(f"Email Queue Length: {stats.get('email_queue_length', 'N/A')}")
        print(f"Dead Letter Queue Length: {stats.get('dead_letter_queue', 'N/A')}")
        print(f"PDF Queue Failed Jobs: {stats.get('pdf_queue_failed', 'N/A')}")
        print(f"Email Queue Failed Jobs: {stats.get('email_queue_failed', 'N/A')}")
        print(f"Total Workers: {worker_stats.get('total_workers', 'N/A')}")
        print(f"Active Workers: {worker_stats.get('active_workers', 'N/A')}")
        print(f"Idle Workers: {worker_stats.get('idle_workers', 'N/A')}")
    except Exception as e:
        print(f"Error getting queue stats: {e}")
    
    print("="*60)

def test_single_failure():

    print("\nTEST 1: Single Job Guaranteed Failure")
    print("-" * 40)
    
    try:
        pdf_queue = get_pdf_queue()
        order_data = create_test_order_data(order_id=9001, customer_email="test.fail@example.com")

        job = pdf_queue.enqueue(
            generate_pdf_task_with_failures,
            order_data=order_data,
            failure_mode="always",
            job_timeout=60,
            retry=Retry(max=2, interval=[5, 10]),
            failure_ttl=3600,

            on_failure="app.services.redis_config.move_to_dead_letter_queue",
        )
        
        print(f"Enqueued job {job.id} that will fail after 2 retries")
        return job
        
    except Exception as e:
        print(f"Error in test_single_failure: {e}")
        return None

def test_timeout_scenario():
    print("\nTEST 2: Timeout Scenario (Fast)")
    print("-" * 40)
    
    try:
        pdf_queue = get_pdf_queue()
        order_data = create_test_order_data(order_id=9002, customer_email="test.timeout@example.com")
        
        job = pdf_queue.enqueue(
            generate_pdf_task_with_failures,
            order_data=order_data,
            failure_mode="timeout",
            job_timeout=10, 
            retry=Retry(max=1, interval=[3]),
            failure_ttl=3600,
            on_failure="app.services.redis_config.move_to_dead_letter_queue",
        )
        
        print(f"Enqueued job {job.id} that will timeout in 10 seconds")
        return job
        
    except Exception as e:
        print(f"Error in test_timeout_scenario: {e}")
        return None

def test_various_failures():
    print("\nTEST 3: Various Failure Types")
    print("-" * 40)
    
    failure_modes = ["memory", "network", "file_not_found", "database"]
    jobs = []
    
    try:
        pdf_queue = get_pdf_queue()
        
        for i, failure_mode in enumerate(failure_modes):
            order_data = create_test_order_data(
                order_id=9010 + i, 
                customer_email=f"test.{failure_mode}@example.com"
            )
            
            job = pdf_queue.enqueue(
                generate_pdf_task_with_failures,
                order_data=order_data,
                failure_mode=failure_mode,
                job_timeout=60,
                retry=Retry(max=2, interval=[3, 6]),
                failure_ttl=3600,
                on_failure="app.services.redis_config.move_to_dead_letter_queue",
            )
            
            jobs.append(job)
            print(f"Enqueued job {job.id} with {failure_mode} failure mode")
        
        return jobs
        
    except Exception as e:
        print(f"Error in test_various_failures: {e}")
        return []

def test_dead_letter_processing():
    print("\nTEST 4: Direct Dead Letter Queue Processing")
    print("-" * 40)
    
    try:
        dlq = get_dead_letter_queue()
        
        test_job_data = {
            "original_func": "generate_pdf_task_with_failures",
            "args": [create_test_order_data(order_id=9999)],
            "kwargs": {"failure_mode": "test"},
            "failure_reason": "Test failure for dead letter processing",
            "original_job_id": "test-job-123",
        }
        
        job = dlq.enqueue(
            dead_letter_handler,
            job_data=test_job_data,
            timeout=60,
        )
        
        print(f"Added test job {job.id} directly to dead letter queue")
        return job
        
    except Exception as e:
        print(f"Error in test_dead_letter_processing: {e}")
        return None

def monitor_jobs(jobs, duration=60):
    if not jobs:
        print("No jobs to monitor")
        return
        
    print(f"\MONITORING JOBS FOR {duration} SECONDS")
    print("-" * 40)
    
    start_time = time.time()
    
    while time.time() - start_time < duration:
        print_queue_status()
        
        print(f"\nJOB STATUSES (showing first 5):")
        active_jobs = [j for j in jobs if j is not None][:5]
        
        for i, job in enumerate(active_jobs):
            try:
                job.refresh()
                status = job.get_status()
                print(f"Job {i+1} ({job.id[:8]}...): {status}")
                
                if status == 'failed':
                    exc_info = getattr(job, 'exc_info', 'No exception info available')
                    print(f"  Failure: {str(exc_info)[:100]}...")
                    
            except Exception as e:
                print(f"Job {i+1}: Error checking status - {e}")
        
        elapsed = int(time.time() - start_time)
        print(f"\nTime elapsed: {elapsed}s / {duration}s")
        
        if elapsed >= duration:
            break
            
        time.sleep(10)

def cleanup_queues():
    print("\nCLEANING UP QUEUES")
    print("-" * 40)
    
    try:
        pdf_queue = get_pdf_queue()
        email_queue = get_email_queue()
        dlq = get_dead_letter_queue()
        
        pdf_queue.empty()
        email_queue.empty()
        dlq.empty()
        
        pdf_queue.failed_job_registry.requeue_all()
        email_queue.failed_job_registry.requeue_all()
        
        print("All queues cleaned up!")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")

def main():
    print("STARTING DEAD LETTER QUEUE TESTS (FIXED VERSION)")
    print("="*60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        cleanup_queues()
        return
    
    print_queue_status()
    
    all_jobs = []
    
    try:
        print("\n RUNNING TESTS...")
        
        job1 = test_single_failure()
        if job1:
            all_jobs.append(job1)
        
        job2 = test_timeout_scenario()
        if job2:
            all_jobs.append(job2)
        
        jobs3 = test_various_failures()
        all_jobs.extend(jobs3)
        
        job4 = test_dead_letter_processing()
        if job4:
            all_jobs.append(job4)
        
        valid_jobs = [j for j in all_jobs if j is not None]
        print(f"\nTESTS ENQUEUED ({len(valid_jobs)} total jobs)")
        
        if valid_jobs:
            monitor_jobs(valid_jobs, duration=90)
        
        print("\nFINAL QUEUE STATUS:")
        print_queue_status()
        
        try:
            dlq = get_dead_letter_queue()
            dlq_jobs = dlq.jobs
            print(f"\nDEAD LETTER QUEUE CONTAINS {len(dlq_jobs)} JOBS:")
            for job in dlq_jobs[:10]: 
                print(f"  - Job {job.id}: {job.func_name}")
        except Exception as e:
            print(f"Error checking dead letter queue: {e}")
        
    except KeyboardInterrupt:
        print("\Test interrupted by user")
        print_queue_status()
    
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        print_queue_status()

if __name__ == "__main__":
    main()