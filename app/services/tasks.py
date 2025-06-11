import time
from typing import Dict, Any
from app.config.redis_config import get_email_queue

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
    """Generate PDF and update order state to INVOICE_GENERATED"""
    order_id = order_data.get('order_id', 'unknown')
    print(f"🔄 Starting PDF generation for order {order_id}")
    print(f"📋 Order details: {order_data}")
    
    try:
        # Import OrderState here to avoid initialization issues
        from app.models.order import OrderState
        
        # Simulate PDF generation
        time.sleep(3)
        pdf_filename = f"order_{order_id}.pdf"
        print(f"✅ PDF generated: {pdf_filename}")
        
        # Update order state to INVOICE_GENERATED
        if update_order_state(order_id, OrderState.INVOICE_GENERATED):
            print(f"📄 Order {order_id} marked as INVOICE_GENERATED")
            
            # Queue email task
            email_queue = get_email_queue()
            email_job = email_queue.enqueue(
                send_email_task,
                order_data=order_data,
                pdf_filename=pdf_filename,
                job_timeout=300
            )
            print(f"📧 Email task queued with job ID: {email_job.id}")
            
            return f"PDF generated successfully: {pdf_filename}"
        else:
            raise Exception("Failed to update order state to INVOICE_GENERATED")
            
    except Exception as e:
        print(f"❌ PDF generation failed for order {order_id}: {e}")
        # Optionally, you might want to set order to failed state here
        raise e

def send_email_task(order_data: Dict[str, Any], pdf_filename: str) -> bool:
    """Send email and update order state to EMAIL_SENT"""
    order_id = order_data.get('order_id', 'unknown')
    customer_email = order_data.get('customer_email', 'unknown@example.com')
    
    print(f"📧 Starting email sending for order: {order_id}")
    print(f"📎 PDF attachment: {pdf_filename}")
    print(f"📬 Recipient: {customer_email}")
    
    try:
        # Import OrderState here to avoid initialization issues
        from app.models.order import OrderState
        
        # Simulate email sending
        time.sleep(2)
        print(f"✅ Email sent successfully to {customer_email}")
        
        # Update order state to EMAIL_SENT
        if update_order_state(order_id, OrderState.EMAIL_SENT):
            print(f"🎉 Order {order_id} processing completed! State: EMAIL_SENT")
            return True
        else:
            raise Exception("Failed to update order state to EMAIL_SENT")
            
    except Exception as e:
        print(f"❌ Email sending failed for order {order_id}: {e}")
        # Optionally, you might want to set order to failed state here
        raise e