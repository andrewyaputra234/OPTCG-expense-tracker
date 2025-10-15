"""
Simple database recreation script
"""

import os
from app import create_app

def recreate_database():
    """Create a fresh database with all tables"""
    
    # Create Flask app without importing the existing app function
    from flask import Flask
    from models import db, InventoryCard, PriceHistory, Card, Collection, WishlistItem
    
    app = Flask(__name__, instance_relative_config=True)
    
    # Create instance directory if it doesn't exist
    os.makedirs(app.instance_path, exist_ok=True)
    
    # Configure new database
    db_name = 'one_piece_tcg_v2.sqlite'
    db_path = os.path.join(app.instance_path, db_name)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        print(f"Creating fresh database: {db_path}")
        
        # Create all tables
        db.create_all()
        
        # Verify tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        print(f"Tables created: {tables}")
        
        # Check specific tables
        required_tables = ['card', 'collection', 'wishlist_item', 'inventory_card', 'price_history']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
        else:
            print("✅ All required tables created successfully!")
            
        # Show columns for inventory_card table
        if 'inventory_card' in tables:
            columns = [col['name'] for col in inspector.get_columns('inventory_card')]
            print(f"InventoryCard columns: {columns}")
        
        print(f"Database file created at: {db_path}")
        return db_name

if __name__ == "__main__":
    new_db = recreate_database()
    print(f"\nNew database created: {new_db}")
    print("Update your app.py to use this database or rename it to replace the old one.")