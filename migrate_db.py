"""
Database migration script to update the schema with inventory tables
"""

import os
from app import create_app
from models import db

def migrate_database():
    """Recreate the database with the new schema"""
    app = create_app()
    
    with app.app_context():
        # Get the database path
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        
        print(f"Database path: {db_path}")
        
        # Check if database exists
        if os.path.exists(db_path):
            print("Existing database found. Creating backup...")
            backup_path = db_path + '.backup'
            
            # Create backup
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"Backup created: {backup_path}")
            
            # Try to rename the old database instead of deleting it
            try:
                old_db_path = db_path + '.old'
                if os.path.exists(old_db_path):
                    os.remove(old_db_path)
                os.rename(db_path, old_db_path)
                print("Old database renamed.")
            except Exception as e:
                print(f"Could not rename old database: {e}")
                print("Will create new database with different name...")
                # Create app with new database name
                new_db_path = db_path.replace('.sqlite', '_new.sqlite')
                app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + new_db_path
                # Re-initialize database with new path
                db.init_app(app)
        
        # Create new database with updated schema
        print("Creating new database with updated schema...")
        db.create_all()
        print("Database migration completed successfully!")
        
        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Tables created: {tables}")
        
        # Check if inventory tables exist
        if 'inventory_card' in tables and 'price_history' in tables:
            print("✓ Inventory tables created successfully!")
        else:
            print("✗ Inventory tables not found!")

if __name__ == "__main__":
    migrate_database()