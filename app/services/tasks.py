import time
from typing import Dict, Any
from app.config.redis_config import get_email_queue

def generate_pdf_task(order_data: Dict[str, Any]) -> str:

    print(f"Starting PDF generation for order {order_data.get('order_id', 'unknwon')}")
    print(f"Order details: {order_data}")

    time.sleep(3)

    pdf_filename=f"order_{order_data.get('order_id'), 'unknown'}.pdf"
    print(f"PDF generated")

    email_queue = get_email_queue()
    email_job = email_queue.enqueue(
        send_email_task,
        order_data=order_data,
        pdf_filename=pdf_filename,
        job_timeout=300
    )

def send_email_task(order_data: Dict[str, Any], pdf_filename: str) -> bool:

    print(f"📧 Starting email sending for order: {order_data.get('order_id', 'unknown')}")
    print(f"📎 PDF attachment: {pdf_filename}")
    print(f"📬 Recipient: {order_data.get('customer_email', 'unknown@example.com')}")
    
    time.sleep(2)
    
    print(f"✅ Email sent successfully to {order_data.get('customer_email', 'unknown@example.com')}")
    print(f"🎉 Order {order_data.get('order_id', 'unknown')} processing completed!")
    
    return True