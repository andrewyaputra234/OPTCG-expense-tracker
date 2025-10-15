"""
Migration script to add manual price override fields to InventoryCard model
Run this once to update existing databases with the new fields
"""

import sqlite3
from datetime import datetime
import os

def add_manual_override_columns():
    """Add manual price override columns to InventoryCard table"""
    
    # Database path
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'one_piece_tcg.sqlite')
    
    if not os.path.exists(db_path):
        print("Database not found. Will be created when you run the app.")
        return
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(inventory_card)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            ('manual_price_yen', 'REAL'),
            ('manual_price_sgd', 'REAL'), 
            ('is_manual_override', 'BOOLEAN DEFAULT 0'),
            ('manual_price_date', 'DATETIME')
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in columns:
                print(f"Adding column: {column_name}")
                cursor.execute(f"ALTER TABLE inventory_card ADD COLUMN {column_name} {column_type}")
            else:
                print(f"Column {column_name} already exists")
        
        conn.commit()
        print("✅ Manual override columns added successfully!")
        
    except Exception as e:
        print(f"❌ Error adding columns: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_manual_override_columns()