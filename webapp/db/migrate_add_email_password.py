"""
Migration Script: Add email and password columns to guests table if they don't exist

This script:
1. Checks if email and password columns exist in guests table
2. Adds them if they don't exist
3. Safe to run multiple times
"""

import sqlite3
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import get_connection


def migrate_add_email_password():
    """Add email and password columns to guests table if they don't exist"""
    
    print("\n" + "="*70)
    print("🔄 MIGRATION: Adding email and password columns to guests table")
    print("="*70 + "\n")
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Check current columns
        cur.execute("PRAGMA table_info(guests)")
        columns = {col[1]: col for col in cur.fetchall()}
        column_names = list(columns.keys())
        
        print("📋 Current columns in guests table:")
        for col_name in column_names:
            print(f"  - {col_name}")
        print()
        
        changes_made = False
        
        # Check and add email column
        if 'email' not in column_names:
            print("📝 Adding 'email' column...")
            cur.execute("ALTER TABLE guests ADD COLUMN email TEXT")
            print("✅ Column 'email' added successfully!\n")
            changes_made = True
        else:
            print("✅ Column 'email' already exists\n")
        
        # Check and add password column
        if 'password' not in column_names:
            print("📝 Adding 'password' column...")
            cur.execute("ALTER TABLE guests ADD COLUMN password TEXT")
            print("✅ Column 'password' added successfully!\n")
            changes_made = True
        else:
            print("✅ Column 'password' already exists\n")
        
        # Commit changes
        if changes_made:
            conn.commit()
            print("\n" + "="*70)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print("="*70)
            print("\nColumns added:")
            print("  - email TEXT")
            print("  - password TEXT")
            print("\n")
        else:
            print("\n" + "="*70)
            print("ℹ️  NO CHANGES NEEDED - All columns already exist")
            print("="*70 + "\n")
        
        # Show updated schema
        cur.execute("PRAGMA table_info(guests)")
        columns = cur.fetchall()
        
        print("📋 Updated guests table schema:")
        print("-"*70)
        print(f"{'Column Name':<20} {'Type':<15} {'Not Null':<10} {'Default'}")
        print("-"*70)
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            not_null = "YES" if col[3] == 1 else "NO"
            default = col[4] if col[4] else "NULL"
            print(f"{col_name:<20} {col_type:<15} {not_null:<10} {default}")
        print("-"*70 + "\n")
        
        return True
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"\n❌ Migration Error: {e}")
        print("Rolling back changes...\n")
        return False
    
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Unexpected Error: {e}")
        print("Rolling back changes...\n")
        return False
    
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        success = migrate_add_email_password()
        if success:
            print("💡 You can now run guest_service.py")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
