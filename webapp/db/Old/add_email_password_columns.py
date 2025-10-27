"""
Quick script to add email and password columns to the guests table
"""

import sqlite3
import os

# Database path
db_path = "../data/WhiteHouse.db"

if not os.path.exists(db_path):
    print(f"❌ Database not found at: {db_path}")
    print("Creating database...")
    # Create the data directory if it doesn't exist
    os.makedirs("../data", exist_ok=True)

print(f"\n📁 Connecting to database: {db_path}\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if guests table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guests'")
    if not cursor.fetchone():
        print("❌ Guests table doesn't exist. Creating it...")
        cursor.execute("""
        CREATE TABLE guests (
            guest_id    VARCHAR(20) PRIMARY KEY,
            name        VARCHAR(100) NOT NULL,
            email       TEXT,
            password    TEXT,
            phone       TEXT,
            phone_number TEXT,
            bed_no      VARCHAR(10),
            guest_type  VARCHAR(20) DEFAULT 'Resident' CHECK(guest_type IN ('Owner','Employee','Resident','Others')),
            status      VARCHAR(20) DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'closed'))
        )
        """)
        print("✅ Guests table created successfully!\n")
    else:
        print("✅ Guests table exists\n")
        
        # Check current columns
        cursor.execute("PRAGMA table_info(guests)")
        columns = {col[1]: col for col in cursor.fetchall()}
        column_names = list(columns.keys())
        
        print("📋 Current columns:")
        for col_name in column_names:
            print(f"  - {col_name}")
        print()
        
        # Add email column if it doesn't exist
        if 'email' not in column_names:
            print("📝 Adding 'email' column...")
            cursor.execute("ALTER TABLE guests ADD COLUMN email TEXT")
            print("✅ Column 'email' added!\n")
        else:
            print("✅ Column 'email' already exists\n")
        
        # Add password column if it doesn't exist
        if 'password' not in column_names:
            print("📝 Adding 'password' column...")
            cursor.execute("ALTER TABLE guests ADD COLUMN password TEXT")
            print("✅ Column 'password' added!\n")
        else:
            print("✅ Column 'password' already exists\n")
        
        # Add phone column if it doesn't exist
        if 'phone' not in column_names:
            print("📝 Adding 'phone' column...")
            cursor.execute("ALTER TABLE guests ADD COLUMN phone TEXT")
            print("✅ Column 'phone' added!\n")
        else:
            print("✅ Column 'phone' already exists\n")
        
        # Add phone_number column if it doesn't exist
        if 'phone_number' not in column_names:
            print("📝 Adding 'phone_number' column...")
            cursor.execute("ALTER TABLE guests ADD COLUMN phone_number TEXT")
            print("✅ Column 'phone_number' added!\n")
        else:
            print("✅ Column 'phone_number' already exists\n")
    
    # Commit changes
    conn.commit()
    
    # Show final schema
    print("\n" + "="*70)
    print("📋 Final guests table schema:")
    print("="*70)
    cursor.execute("PRAGMA table_info(guests)")
    columns = cursor.fetchall()
    
    print(f"\n{'#':<5} {'Column':<20} {'Type':<15} {'Not Null':<10} {'Default'}")
    print("-"*70)
    for col in columns:
        col_id = col[0]
        col_name = col[1]
        col_type = col[2]
        not_null = "YES" if col[3] == 1 else "NO"
        default = col[4] if col[4] else "-"
        print(f"{col_id:<5} {col_name:<20} {col_type:<15} {not_null:<10} {default}")
    print("-"*70)
    
    print("\n✅ Database updated successfully!")
    print("\n💡 You can now use guest_service.py\n")
    
except Exception as e:
    print(f"\n❌ Error: {e}\n")
    conn.rollback()
finally:
    conn.close()
