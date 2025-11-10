import os
import shutil
import json
import sqlite3
from datetime import datetime
from models import db, InventoryCard, Collection, Card

def export_database():
    """Export the database to a backup file"""
    try:
        # Create backups directory if it doesn't exist
        if not os.path.exists('backups'):
            os.makedirs('backups')
        
        # Create timestamp for backup file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Backup SQLite database
        source_db = 'instance/one_piece_tcg.sqlite'
        backup_db = f'backups/one_piece_tcg_{timestamp}.sqlite'
        
        # Copy the database file
        if os.path.exists(source_db):
            shutil.copy2(source_db, backup_db)
            print(f"Database backed up to: {backup_db}")
        
        # Export data to JSON for portability
        data = {
            'inventory_cards': [],
            'collections': [],
            'cards': []
        }
        
        # Connect to the database
        conn = sqlite3.connect(source_db)
        conn.row_factory = sqlite3.Row
        
        # Export inventory cards
        cursor = conn.execute('SELECT * FROM inventory_card')
        for row in cursor:
            data['inventory_cards'].append(dict(row))
        
        # Export collections
        cursor = conn.execute('SELECT * FROM collection')
        for row in cursor:
            data['collections'].append(dict(row))
        
        # Export cards
        cursor = conn.execute('SELECT * FROM card')
        for row in cursor:
            data['cards'].append(dict(row))
        
        # Save to JSON file
        json_backup = f'backups/database_backup_{timestamp}.json'
        with open(json_backup, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Data exported to JSON: {json_backup}")
        print("\nTo restore this backup on another device:")
        print(f"1. Copy both {os.path.basename(backup_db)} and {os.path.basename(json_backup)}")
        print("2. Place them in the same folder as this script on the new device")
        print("3. Run: python backup_database.py restore <backup_name>")
        print("   Example: python backup_database.py restore one_piece_tcg_20251110_120000")
        
        return True
    except Exception as e:
        print(f"Error during backup: {e}")
        return False

def list_backups():
    """List all available backups with their dates"""
    try:
        if not os.path.exists('backups'):
            print("No backups folder found.")
            return

        backups = []
        # Get all SQLite backup files
        for file in os.listdir('backups'):
            if file.startswith('one_piece_tcg_') and file.endswith('.sqlite'):
                backup_path = os.path.join('backups', file)
                # Get file creation/modification time
                timestamp = os.path.getmtime(backup_path)
                date = datetime.fromtimestamp(timestamp)
                
                # Get backup size
                size = os.path.getsize(backup_path)
                size_mb = size / (1024 * 1024)  # Convert to MB
                
                # Extract timestamp from filename
                backup_date = file.replace('one_piece_tcg_', '').replace('.sqlite', '')
                
                backups.append({
                    'filename': file,
                    'date': date,
                    'size': size_mb,
                    'backup_date': backup_date
                })
        
        if not backups:
            print("No backups found.")
            return
        
        print("\nAvailable Backups:")
        print("=" * 80)
        print(f"{'Backup Name':<30} {'Created On':<20} {'Size':<10}")
        print("-" * 80)
        
        for backup in sorted(backups, key=lambda x: x['date'], reverse=True):
            print(f"{backup['backup_date']:<30} {backup['date'].strftime('%Y-%m-%d %H:%M:%S'):<20} {backup['size']:.2f}MB")
        
        print("\nTo restore a backup, use:")
        print("python backup_database.py restore <backup_name>")
        print("Example: python backup_database.py restore " + backups[0]['backup_date'])
        
    except Exception as e:
        print(f"Error listing backups: {e}")

def restore_database(backup_name):
    """Restore the database from a backup file"""
    try:
        # Check if backup files exist
        sqlite_backup = f'backups/{backup_name}.sqlite'
        json_backup = f'backups/database_backup_{backup_name}.json'
        
        if not os.path.exists(sqlite_backup) or not os.path.exists(json_backup):
            print(f"Backup files not found. Make sure both {sqlite_backup} and {json_backup} exist.")
            return False
        
        # Create instance directory if it doesn't exist
        if not os.path.exists('instance'):
            os.makedirs('instance')
        
        # Restore SQLite database
        target_db = 'instance/one_piece_tcg.sqlite'
        shutil.copy2(sqlite_backup, target_db)
        print(f"Database restored from: {sqlite_backup}")
        
        print("Database restore completed successfully!")
        return True
    except Exception as e:
        print(f"Error during restore: {e}")
        return False

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        # Default to backup if no command provided
        print("Creating backup...")
        export_database()
    elif sys.argv[1] == 'backup':
        print("Creating backup...")
        export_database()
    elif sys.argv[1] == 'list':
        list_backups()
    elif sys.argv[1] == 'restore' and len(sys.argv) == 3:
        print(f"Restoring from backup: {sys.argv[2]}")
        restore_database(sys.argv[2])
    else:
        print("Usage:")
        print("  To create backup: python backup_database.py backup")
        print("  To list backups: python backup_database.py list")
        print("  To restore backup: python backup_database.py restore <backup_name>")
        print("  Example: python backup_database.py restore one_piece_tcg_20251110_120000")