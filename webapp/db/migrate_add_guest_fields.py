"""
Migration script to add email, password, and phone_number fields to guests table.
Run this once to add the new fields to the existing database.
"""
import sqlite3
import os

# Database path - adjust if needed
DB_PATH = "./data/WhiteHouse.db"

def migrate():
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {os.path.abspath(DB_PATH)}")
        return
    
    print(f"Connecting to database: {os.path.abspath(DB_PATH)}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    print("Checking current guests table schema...")
    
    # Check current columns in guests table
    cur.execute("PRAGMA table_info(guests)")
    columns = {row[1] for row in cur.fetchall()}
    
    print(f"Current columns: {columns}")
    
    # Add email column if not exists
    if 'email' not in columns:
        print("Adding 'email' column to guests table...")
        cur.execute("ALTER TABLE guests ADD COLUMN email TEXT")
        print("✅ 'email' column added")
    else:
        print("✅ 'email' column already exists")
    
    # Add password column if not exists
    if 'password' not in columns:
        print("Adding 'password' column to guests table...")
        cur.execute("ALTER TABLE guests ADD COLUMN password TEXT")
        print("✅ 'password' column added")
    else:
        print("✅ 'password' column already exists")
    
    # Add phone_number column if not exists (if 'phone' doesn't already serve this purpose)
    if 'phone_number' not in columns:
        print("Adding 'phone_number' column to guests table...")
        cur.execute("ALTER TABLE guests ADD COLUMN phone_number TEXT")
        print("✅ 'phone_number' column added")
    else:
        print("✅ 'phone_number' column already exists")
    
    # Note: The existing 'phone' column will remain for backward compatibility
    # New code should use 'phone_number' for consistency
    
    conn.commit()
    
    print("\n📊 Updated schema:")
    cur.execute("PRAGMA table_info(guests)")
    for row in cur.fetchall():
        print(f"  - {row[1]} ({row[2]})")
    
    conn.close()
    print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
