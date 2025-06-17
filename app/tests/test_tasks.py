import random
import time
from typing import Dict, Any
from rq import Retry

class MockOrderState:
    PENDING = "pending"
    INVOICE_GENERATED = "invoice_generated"
    PDF_FAILED = "pdf_failed"
    EMAIL_SENT = "email_sent"
    EMAIL_FAILED = "email_failed"

def get_db_session():

    class MockSession:
        def query(self, model):
            return MockQuery()
        def commit(self):
            pass
        def rollback(self):
            pass
        def close(self):
            pass
    
    return MockSession()

class MockQuery:
    def filter(self, condition):
        return self
    def first(self):
        class MockOrder:
            def __init__(self):
                self.id = 1
                self.state = MockOrderState.PENDING
        return MockOrder()

def update_order_state(order_id: int, new_state: str):
    try:
        db = get_db_session()
   
        print(f"[MOCK] Order {order_id} state updated to: {new_state}")
        return True
        
    except Exception as e:
        try:
            db.rollback()
        except:
            pass  
        print(f"Error updating order state: {e}")
        return False
    finally:
        try:
            db.close()
        except:
            pass  

def generate_pdf_task_with_failures(order_data: Dict[str, Any], failure_mode: str = "none") -> str:

    print(f"Starting PDF generation for order {order_data.get('order_id', 'unknown')}")
    print(f"Failure mode: {failure_mode}")
    
    start_time = time.time()
    order_id = order_data.get("order_id", "unknown")
    
    try:

        if failure_mode == "always":
            raise Exception("Simulated PDF generation failure - always fails")
        
        elif failure_mode == "random":
            if random.random() < 0.3: 
                raise Exception("Simulated random PDF generation failure")
        
        elif failure_mode == "timeout":

            print("Simulating timeout scenario...")
            time.sleep(400)  
        
        elif failure_mode == "memory":
            raise MemoryError("Simulated out of memory error during PDF generation")
        
        elif failure_mode == "network":
            raise ConnectionError("Simulated network error - could not reach PDF service")
        
        elif failure_mode == "file_not_found":
            raise FileNotFoundError("Simulated error - template file not found")
        
        elif failure_mode == "database":
            raise Exception("Simulated database connection error")
        
        time.sleep(3)
        pdf_filename = f"order_{order_data.get('order_id', 'unknown')}.pdf"
        print(f"PDF generated successfully: {pdf_filename}")
        
        if order_id and order_id != "unknown":
            update_order_state(order_id, MockOrderState.INVOICE_GENERATED)
        
        print(f"PDF generation completed for order {order_id}")
        return pdf_filename
        
    except Exception as e:
        print(f"PDF generation failed for order {order_id}: {e}")
        if order_id and order_id != "unknown":
            update_order_state(order_id, MockOrderState.PDF_FAILED)
        raise

def send_email_task_with_failures(order_data: Dict[str, Any], pdf_filename: str, failure_mode: str = "none") -> bool:
    """Enhanced email sending task with failure simulation"""
    print(f"Starting email sending for order: {order_data.get('order_id', 'unknown')}")
    print(f"PDF attachment: {pdf_filename}")
    print(f"Recipient: {order_data.get('customer_email', 'unknown@example.com')}")
    print(f"Failure mode: {failure_mode}")
    
    try:
        if failure_mode == "always":
            raise Exception("Simulated email sending failure - always fails")
        
        elif failure_mode == "random":
            if random.random() < 0.25:  
                raise Exception("Simulated random email sending failure")
        
        elif failure_mode == "smtp":
            raise ConnectionError("SMTP server unavailable - connection refused")
        
        elif failure_mode == "auth":
            raise Exception("Email authentication failed - invalid credentials")
        
        elif failure_mode == "attachment":
            raise Exception(f"Failed to attach PDF file: {pdf_filename} not found")
        
        elif failure_mode == "recipient":
            raise Exception(f"Invalid recipient email: {order_data.get('customer_email', 'unknown@example.com')}")
        
        time.sleep(2)
        print(f"Email sent successfully to {order_data.get('customer_email', 'unknown@example.com')}")
        
        order_id = order_data.get("order_id")
        if order_id:
            update_order_state(order_id, MockOrderState.EMAIL_SENT)
        
        print(f"Order {order_data.get('order_id', 'unknown')} processing completed!")
        return True
        
    except Exception as e:
        print(f"Email sending failed for order {order_data.get('order_id', 'unknown')}: {e}")
        order_id = order_data.get("order_id")
        if order_id:
            update_order_state(order_id, MockOrderState.EMAIL_FAILED)
        raise

def dead_letter_handler(job_data: Dict[str, Any]):
    print("=" * 50)
    print("PROCESSING DEAD LETTER QUEUE ITEM")
    print("=" * 50)
    
    original_func = job_data.get("original_func", "unknown")
    failure_reason = job_data.get("failure_reason", "unknown")
    original_job_id = job_data.get("original_job_id", "unknown")
    args = job_data.get("args", [])
    kwargs = job_data.get("kwargs", {})
    
    print(f"Original Function: {original_func}")
    print(f"Original Job ID: {original_job_id}")
    print(f"Failure Reason: {failure_reason}")
    print(f"Arguments: {args}")
    print(f"Keyword Arguments: {kwargs}")
    
    try:
     
        order_data = None
        if args and isinstance(args[0], dict) and "order_id" in args[0]:
            order_data = args[0]
        elif "order_data" in kwargs:
            order_data = kwargs["order_data"]
        
        if order_data and "order_id" in order_data:
            order_id = order_data["order_id"]
            print(f"Order {order_id} requires manual review due to repeated failures")

        print(f"Dead letter item logged and processed")
        
        return True
        
    except Exception as e:
        print(f"Error processing dead letter item: {e}")
        raise

def create_test_order_data(order_id: int, customer_email: str = "test@example.com") -> Dict[str, Any]:
    return {
        "order_id": order_id,
        "customer_email": customer_email,
        "customer_name": f"Test Customer {order_id}",
        "order_total": 99.99,
        "items": [
            {"name": "Test Product", "quantity": 1, "price": 99.99}
        ]
    }