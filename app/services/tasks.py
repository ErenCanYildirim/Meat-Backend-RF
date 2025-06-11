import time
from typing import Dict, Any
from app.config.redis_config import get_email_queue

from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.order import Order, OrderState


def get_db_session():
    """Get database session using your existing get_db function"""
    # Import here to avoid circular imports and model loading issues
    from app.config.database import get_db
    return next(get_db())

def update_order_state(order_id: int, new_state):
    """Update order state in database"""
    db = get_db_session()
    try:
        # Import models here to avoid initialization issues
        from app.models.order import Order, OrderState
        
        order = db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.state = new_state
            db.commit()
            print(f"✅ Order {order_id} state updated to: {new_state}")
            return True
        else:
            print(f"❌ Order {order_id} not found")
            return False
    except Exception as e:
        db.rollback()
        print(f"❌ Error updating order state: {e}")
        return False
    finally:
        db.close()

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