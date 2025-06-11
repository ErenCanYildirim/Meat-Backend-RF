import sys
import time
from datetime import datetime

sys.path.append("/app")
sys.path.append("./app")


def create_test_order():
    """Create a test order in the database"""
    print("🔨 Creating test order...")

    try:
        from app.config.database import get_db
        from app.models.order import Order, OrderState
        from app.models.user import User  # Adjust path as needed
        from app.models.product import Product  # Adjust path as needed
        from app.models.order import OrderItem  # Adjust path as needed

        db = next(get_db())

        # Create or get test user
        test_email = "test@example.com"
        user = db.query(User).filter(User.email == test_email).first()
        if not user:
            print(f"⚠️ User {test_email} not found - creating test user...")
            # Create a test user - adjust based on your User model requirements
            user = User(
                email=test_email,
                hashed_password="dummy_hash",  # You might need proper password hashing
                company_name=f"Test Company {int(time.time())}",  # Unique company name
                is_active=True,
            )
            db.add(user)
            db.commit()
            print(f"✅ Test user created: {test_email}")

        # Get a test product (assume one exists)
        test_product = db.query(Product).first()
        if not test_product:
            print(f"⚠️ No products found in database - you may need to create one first")
            return None

        # Create order
        order = Order(
            user_email=test_email,
            order_date=datetime.now(),
            state=OrderState.ORDER_PLACED,
        )

        db.add(order)
        db.commit()
        db.refresh(order)

        # Add order item
        order_item = OrderItem(
            order_id=order.id, product_id=test_product.id, quantity=2
        )
        db.add(order_item)
        db.commit()

        order_id = order.id
        print(f"✅ Test order created with ID: {order_id}")
        print(f"📊 Initial state: {order.state}")
        print(f"🛍️ Order items: {len(order.order_items)} items")

        return order_id

    except Exception as e:
        print(f"❌ Error creating test order: {e}")
        import traceback

        traceback.print_exc()
        return None
    finally:
        db.close()


def check_order_state(order_id):
    """Check current order state"""
    if not order_id:
        return None

    try:
        from app.config.database import get_db
        from app.models.order import Order

        db = next(get_db())
        order = db.query(Order).filter(Order.id == order_id).first()

        if order:
            print(f"📊 Order {order_id} current state: {order.state}")
            return order.state
        else:
            print(f"❌ Order {order_id} not found")
            return None

    except Exception as e:
        print(f"❌ Error checking order state: {e}")
        return None
    finally:
        db.close()


def test_order_state_flow():
    """Test the complete order state flow"""
    print("🧪 Testing Order State Flow")
    print("=" * 60)

    # Step 1: Create test order
    order_id = create_test_order()
    if not order_id:
        print("Cannot proceed without order")
        return

    # Step 2: Check initial state
    initial_state = check_order_state(order_id)
    if initial_state != "order_placed":
        print(f"⚠️ Expected 'order_placed', got '{initial_state}'")

    # Step 3: Queue PDF generation job
    print(f"\n📄 Queuing PDF generation...")
    try:
        from app.config.redis_config import get_pdf_queue
        from app.services.tasks import generate_pdf_task

        order_data = {
            "order_id": order_id,
            "user_email": "test@example.com",
            "order_date": datetime.now().isoformat(),
            "state": "order_placed",
            "customer_name": "Test Company",
            "customer_email": "test@example.com",
            "order_items": [
                {
                    "id": 1,
                    "product_id": 101,
                    "quantity": 2,
                    "product_description": "Test Product A",
                }
            ],
        }

        pdf_queue = get_pdf_queue()
        job = pdf_queue.enqueue(
            generate_pdf_task, order_data=order_data, job_timeout=300
        )

        print(f"✅ PDF job queued: {job.id}")

        # Step 4: Monitor progress
        print(f"\n⏱️ Monitoring order state changes...")

        for i in range(12):  # Check for 60 seconds (5 sec intervals)
            time.sleep(5)
            current_state = check_order_state(order_id)
            print(f"⏰ Check {i+1}: State = {current_state}")

            if current_state == "email_sent":
                print(f"🎉 Order processing completed successfully!")
                break

        # Final state check
        print(f"\n" + "=" * 60)
        final_state = check_order_state(order_id)
        print(f"🏁 Final order state: {final_state}")

        # Expected flow: order_placed → invoice_generated → email_sent
        if final_state == "email_sent":
            print(f"✅ SUCCESS: Order state flow completed correctly!")
        else:
            print(f"⚠️ INCOMPLETE: Expected 'email_sent', got '{final_state}'")

    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback

        traceback.print_exc()


def main():
    print("Order State Flow Test")
    print("=" * 60)
    print("This test will:")
    print("1. Create a test order (ORDER_PLACED)")
    print("2. Queue PDF generation job")
    print("3. Monitor state changes")
    print("4. Verify final state is EMAIL_SENT")
    print("=" * 60)

    test_order_state_flow()

    print(f"\n💡 Next steps:")
    print("   - Check worker logs: docker-compose logs worker")
    print("   - Verify database: SELECT id, state FROM orders;")


if __name__ == "__main__":
    main()
