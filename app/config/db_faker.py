import random
from faker import Faker
from datetime import datetime, timedelta 

from sqlalchemy.orm import Session
from app.config.database import SessionLocal
from app.models.user import User, Role
from app.models.order import Order, OrderItem, OrderState
from app.models.product import Product, ProductCategory
from app.models.base import Base
from app.crud.roles import get_role_by_name


fake = Faker()

NUM_USERS = 50
MAX_ORDERS_PER_USER = 60
MAX_ITEMS_PER_ORDER = 5
ORDER_DATE_SPREAD_DAYS = 750

def fetch_existing_products(db: Session):
    products = db.query(Product).all()
    if len(products) == 0:
        raise ValueError("No products found in the database.")
    return products

def create_dummy_users(db: Session):
    print("Creating dummy users...")
    customer_role = get_role_by_name(db, "customer")
    users = []
    for _ in range(NUM_USERS):
        user = User(
            email=fake.email(),
            hashed_password="fakehashedpassword",
            company_name = fake.unique.company(),
            is_active=True,
            roles=[customer_role],
        )
        db.add(user)
        users.append(user)
    db.commit()
    print(f"Inserted {len(users)} users.")
    return users

def random_order_date():
    days_ago = random.randint(0, ORDER_DATE_SPREAD_DAYS)
    seconds_offset = random.randint(0, 86400)
    return datetime.now() - timedelta(days=days_ago, seconds=seconds_offset)

def create_dummy_orders(db: Session, users, products):
    print("Creating dummy orders...")
    for user in users:
        num_orders = random.randint(1, MAX_ORDERS_PER_USER)
        for _ in range(num_orders):
            order = Order(
                user_email=user.email,
                state=OrderState.EMAIL_SENT,
                order_date=random_order_date(),
            )
            db.add(order)
            db.flush()  
            num_items = random.randint(1, min(MAX_ITEMS_PER_ORDER, len(products)))
            selected_products = random.sample(products, num_items)
            for product in selected_products:
                item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=random.randint(1, 5),
                )
                db.add(item)
    db.commit()
    print("Inserted orders and order items.")

def populate_dummy_data():
    db = SessionLocal()
    try:
        products = fetch_existing_products(db)
        users = create_dummy_users(db)
        create_dummy_orders(db, users, products)
    finally:
        db.close()

