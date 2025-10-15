"""
Migration script to add category column to inventory_card table
"""

import sqlite3
import os
from app import create_app

def add_category_column():
    """Add category column to existing inventory_card table"""
    app = create_app()
    
    with app.app_context():
        # Get database path
        db_path = os.path.join(app.instance_path, 'one_piece_tcg.sqlite')
        
        if not os.path.exists(db_path):
            print("Database not found. Please create the database first.")
            return False
        
        try:
            # Connect to database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if category column already exists
            cursor.execute("PRAGMA table_info(inventory_card)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'category' in columns:
                print("Category column already exists!")
                return True
            
            # Add category column
            cursor.execute("ALTER TABLE inventory_card ADD COLUMN category VARCHAR(50) DEFAULT 'Regular'")
            
            # Update existing cards based on rarity
            print("Adding category column and setting default values...")
            
            # Set categories based on rarity
            cursor.execute("UPDATE inventory_card SET category = 'SEC' WHERE rarity = 'SEC' OR rarity = 'Secret'")
            cursor.execute("UPDATE inventory_card SET category = 'SR' WHERE rarity = 'SR' OR rarity = 'Super Rare'")
            cursor.execute("UPDATE inventory_card SET category = 'AA LDR' WHERE rarity = 'L' OR rarity = 'Leader'")
            cursor.execute("UPDATE inventory_card SET category = 'Regular' WHERE category IS NULL")
            
            conn.commit()
            print("✅ Category column added successfully!")
            print("📋 Default categories assigned based on existing rarity values")
            
            # Show updated records
            cursor.execute("SELECT name, rarity, category FROM inventory_card")
            records = cursor.fetchall()
            
            if records:
                print("\n📊 Updated inventory records:")
                for name, rarity, category in records:
                    print(f"  - {name} ({rarity}) → {category}")
            else:
                print("No inventory records found.")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error adding category column: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False

if __name__ == "__main__":
    print("=== Adding Category Support to Inventory ===")
    success = add_category_column()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("🎯 You can now categorize your cards as:")
        print("   - Mangas")
        print("   - SP (Special Parallel)")
        print("   - AA LDR (Alternate Art Leaders)")
        print("   - SEC (Secret Rares)")
        print("   - AA (Regular Alternate Arts)")
        print("   - SR (Super Rares)")
        print("\n🔄 Please restart your Flask app to use the new feature.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")