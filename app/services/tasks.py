import time
from enum import Enum
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.redis_config import get_email_queue, retry_failed_job
from app.middleware.prometheus_middleware import (record_email_sent,
                                                  record_pdf_processing_time)
from app.models.order import Order, OrderState
from app.services.email_utils import send_mail_with_attachment


def get_db_session():
    return next(get_db())


def update_order_state(order_id: int, new_state: OrderState):
    db = get_db_session()
    try:

        order = db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.state = new_state
            db.commit()
            print(f"Order {order_id} state updated to: {new_state}")
            return True
        else:
            print(f"Order {order_id} not found")
            return False
    except Exception as e:
        db.rollback()
        print(f"Error updating order state: {e}")
        return False
    finally:
        db.close()


def generate_pdf_task(order_data: Dict[str, Any]) -> str:
    print(f"Starting PDF generation for order {order_data.get('order_id', 'unknown')}")
    print(f"Order details: {order_data}")
    start_time = time.time()
    order_id = order_data.get("order_id", "unknown")

    try:

        time.sleep(3)

        pdf_filename = f"order_{order_data.get('order_id', 'unknown')}.pdf"
        print(f"PDF generated: {pdf_filename}")

        order_id = order_data.get("order_id")
        if order_id:
            update_order_state(order_id, OrderState.INVOICE_GENERATED)

        duration = time.time() - start_time
        record_pdf_processing_time(duration)

        email_queue = get_email_queue()
        email_job = email_queue.enqueue(
            send_email_task,
            order_data=order_data,
            pdf_filename=pdf_filename,
            job_timeout=300,
        )

        return pdf_filename

    except Exception as e:
        print(f"PDF generation failed for order {order_id}: {e}")
        from rq import get_current_job

        current_job = get_current_job()

        if current_job:
            retry_failed_job(current_job.id)
        raise


def send_email_task(order_data: Dict[str, Any], pdf_filename: str) -> bool:
    print(f"Starting email sending for order: {order_data.get('order_id', 'unknown')}")
    print(f"PDF attachment: {pdf_filename}")
    print(f"Recipient: {order_data.get('customer_email', 'unknown@example.com')}")

    try:
        time.sleep(2)

        print(
            f"Email sent successfully to {order_data.get('customer_email', 'unknown@example.com')}"
        )

        order_id = order_data.get("order_id")
        if order_id:
            update_order_state(order_id, OrderState.EMAIL_SENT)

        print(f"Order {order_data.get('order_id', 'unknown')} processing completed!")

        return True

    except Exception as e:
        print(
            f"Email sending failed for order {order_data.get('order_id', 'unknown')} : {e}"
        )
        from rq import get_current_job

        current_job = get_current_job()
        if current_job:
            retry_failed_job(current_job.id)
        raise


# Use this in prod later
def send_email_task_prod(
    order_data: Dict[str, Any], pdf_filename: str, pdf_path: str
) -> bool:
    print(f"Starting email sending for order: {order_data.get('order_id', 'unknown')}")
    print(f"PDF attachment: {pdf_filename}")

    status_code = send_mail_with_attachment(pdf_filename, pdf_path)

    if status_code == 202:
        print(
            f"Email sent successfully to {order_data.get('customer_email', 'unknown@example.com')}"
        )

        order_id = order_data.get("order_id")
        if order_id:
            update_order_state(order_id, OrderState.EMAIL_SENT)

        print(f"Order {order_data.get('order_id', 'unknown')} processing completed!")

        record_email_sent("order_confirmation", "success")
        return True
    else:
        print(f"Email failed to send for order {order_data.get('order_id', 'unknown')}")

        record_email_sent("order_confirmation", "failed")
        return False
