import os 
from pathlib import Path
from sqlalchemy.orm import Session
from app.config.database import SessionLocal, engine
from app.models.base import Base
from app.models.product import Product, ProductCategory

def get_category_from_folder(folder_name:str) -> ProductCategory:
    folder_mapping = {
        "chicken": ProductCategory.CHICKEN,
        "veal": ProductCategory.VEAL,
        "lamb": ProductCategory.LAMB,
        "beef": ProductCategory.BEEF,
        "other": ProductCategory.OTHER
    }
    return folder_mapping.get(folder_name.lower(), ProductCategory.OTHER)

def initialize_products():
    """Initialize products from image files in static directory"""
    print("🚀 Initializing products from image files...")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if products already exist
        existing_count = db.query(Product).count()
        if existing_count > 0:
            print(f"⚠️  Products already exist in database ({existing_count} products). Skipping initialization.")
            return
        
        # Path to product images
        images_dir = Path("app/static/product_images")
        
        if not images_dir.exists():
            print(f"❌ Images directory not found: {images_dir}")
            return
        
        products_added = 0
        
        # Iterate through category folders
        for category_folder in images_dir.iterdir():
            if not category_folder.is_dir():
                continue
                
            category = get_category_from_folder(category_folder.name)
            print(f"📁 Processing {category_folder.name} -> {category.value}")
            
            # Process PNG files in the folder
            for image_file in category_folder.glob("*.png"):
                # Extract description from filename (remove .png extension)
                description = image_file.stem
                
                # Generate image link
                image_link = f"/static/product_images/{category_folder.name}/{image_file.name}"
                
                # Create product
                product = Product(
                    description=description,
                    image_link=image_link,
                    category=category
                )
                
                db.add(product)
                products_added += 1
                print(f"  ✅ Added: {description}")
        
        # Commit all changes
        db.commit()
        print(f"🎉 Successfully initialized {products_added} products!")
        
        # Print summary by category
        print("\n📊 Products by category:")
        for category in ProductCategory:
            count = db.query(Product).filter(Product.category == category).count()
            if count > 0:
                print(f"  {category.value}: {count} products")
                
    except Exception as e:
        print(f"❌ Error initializing products: {e}")
        db.rollback()
        raise
    finally:
        db.close()
    
def reset_products():
    print("Resetting products...")
    db = SessionLocal()
    try:
        deleted_count = db.query(Product).count()
        db.query(Product).delete()
        db.commit()
        print(f"🗑️  Deleted {deleted_count} products")
    except Exception as e:
        print(f"Error resetting products: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    #reset_products()
    pass