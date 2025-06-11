import sys
import os
import time

#Test queue functionality directly

sys.path.append('/app')
sys.path.append('./app')

def test_redis_connection():
    print("Testing Redis connection...")
    
    try:
        from app.config.redis_config import get_redis_connection
        redis_conn = get_redis_connection()
        redis_conn.ping()
        print("✅ Redis connection successful!")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def test_queue_directly():
    """Test queues directly without API"""
    print("\n🧪 Testing queues directly...")
    
    try:
        from app.config.redis_config import get_pdf_queue
        from app.services.tasks import generate_pdf_task
        
        # Sample order data matching your structure
        order_data = {
            "order_id": 123,
            "user_email": "test@example.com",
            "order_date": "2025-06-11T10:30:00",
            "state": "pending",
            "customer_name": "Test Company",
            "customer_email": "test@example.com",
            "order_items": [
                {
                    "id": 1,
                    "product_id": 101,
                    "quantity": 2,
                    "product_description": "Test Product A",
                    "product_category": "Electronics"
                },
                {
                    "id": 2,
                    "product_id": 102,
                    "quantity": 1,
                    "product_description": "Test Product B",
                    "product_category": "Accessories"
                }
            ]
        }
        
        print(f"📋 Test order data prepared")
        print(f"📦 Order ID: {order_data['order_id']}")
        print(f"👤 Customer: {order_data['customer_name']}")
        print(f"📧 Email: {order_data['customer_email']}")
        print(f"🛍️ Items: {len(order_data['order_items'])} products")
        
        # Queue the job
        pdf_queue = get_pdf_queue()
        job = pdf_queue.enqueue(
            generate_pdf_task,
            order_data=order_data,
            job_timeout=300
        )
        
        print(f"✅ Job queued successfully!")
        print(f"🆔 Job ID: {job.id}")
        print(f"📊 Job Status: {job.get_status()}")
        
        return job.id
        
    except Exception as e:
        print(f"❌ Error testing queue: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_job_status(job_id):
    """Check the status of a job"""
    if not job_id:
        return
        
    print(f"\n🔍 Checking job status...")
    
    try:
        from rq.job import Job
        from app.config.redis_config import get_redis_connection
        
        redis_conn = get_redis_connection()
        job = Job.fetch(job_id, connection=redis_conn)
        
        print(f"🆔 Job ID: {job_id}")
        print(f"📊 Status: {job.get_status()}")
        print(f"📅 Created: {job.created_at}")
        print(f"🚀 Started: {job.started_at}")
        print(f"🏁 Ended: {job.ended_at}")
        
        if job.result:
            print(f"📄 Result: {job.result}")
        
        if job.exc_info:
            print(f"❌ Error: {job.exc_info}")
            
    except Exception as e:
        print(f"❌ Error checking job status: {e}")

def check_queue_lengths():
    """Check how many jobs are in each queue"""
    print("\n📊 Checking queue lengths...")
    
    try:
        from app.config.redis_config import get_pdf_queue, get_email_queue
        
        pdf_queue = get_pdf_queue()
        email_queue = get_email_queue()
        
        print(f"📄 PDF Queue: {len(pdf_queue)} jobs")
        print(f"📧 Email Queue: {len(email_queue)} jobs")
        
        # Show job IDs if any
        if len(pdf_queue) > 0:
            pdf_jobs = [job.id for job in pdf_queue.jobs[:5]]  # Show first 5
            print(f"📄 PDF Jobs: {pdf_jobs}")
            
        if len(email_queue) > 0:
            email_jobs = [job.id for job in email_queue.jobs[:5]]  # Show first 5
            print(f"📧 Email Jobs: {email_jobs}")
            
    except Exception as e:
        print(f"❌ Error checking queues: {e}")

def main():
    print("Simple queue test")
    print("=" * 50)

    if not test_redis_connection():
        print("\n Cannot proceed without Redis")
        return
    
    check_queue_lengths()
    job_id = test_queue_directly()

    if job_id:
        print("\n" + "=" * 50)
        print("⏱️ Waiting 3 seconds...")
        time.sleep(3)
        
        # Check job status
        check_job_status(job_id)
        
        # Check queues again
        check_queue_lengths()
        
        print("\n" + "=" * 50)
        print("⏱️ Waiting 10 more seconds for processing...")
        time.sleep(10)
        
        # Final check
        check_job_status(job_id)
        check_queue_lengths()
    
    print("\n" + "=" * 50)
    print("🎉 Simple test completed!")
    print("\n💡 Tips:")
    print("   - Check worker logs: docker-compose logs worker")
    print("   - If jobs aren't processing, restart worker: docker-compose restart worker")
    print("   - Make sure worker container is running: docker-compose ps")

if __name__ == "__main__":
    main()