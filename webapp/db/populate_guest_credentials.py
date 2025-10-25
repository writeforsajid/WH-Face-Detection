"""
Script to populate email, password, and phone_number fields for existing guests.
Uses simple, real Gmail format with a common password and Indian phone numbers.
"""
import sqlite3
import os
import random

# Database path
DB_PATH = "../../data/WhiteHouse.db"

def populate_credentials():
    """Populate email, password, and phone_number for all guests that don't have them."""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {os.path.abspath(DB_PATH)}")
        return
    
    print(f"Connecting to database: {os.path.abspath(DB_PATH)}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Common password for all guests (simple and easy to remember)
    common_password = "Pass@123"
    
    # Indian phone number prefixes (common operators)
    phone_prefixes = ['98', '99', '97', '96', '95', '94', '93', '92', '91', '90', 
                      '89', '88', '87', '86', '85', '84', '83', '82', '81', '80',
                      '79', '78', '77', '76', '75', '74', '73', '72', '71', '70']
    
    # Get all guests without email or phone_number
    cur.execute("SELECT guest_id, name, email, phone_number FROM guests")
    guests = cur.fetchall()
    
    print(f"\nProcessing {len(guests)} guests")
    print("=" * 90)
    
    updated_count = 0
    
    for guest in guests:
        guest_id = guest[0]
        name = guest[1]
        existing_email = guest[2]
        existing_phone = guest[3]
        
        # Create email from name if not exists
        if not existing_email:
            email_username = name.lower().replace(" ", "")
            email = f"{email_username}@gmail.com"
        else:
            email = existing_email
        
        # Generate Indian phone number if not exists
        # Format: +91 XXXXX XXXXX (10 digits after +91)
        if not existing_phone:
            prefix = random.choice(phone_prefixes)
            remaining_8_digits = ''.join([str(random.randint(0, 9)) for _ in range(8)])
            phone_number = f"+91 {prefix}{remaining_8_digits[:3]} {remaining_8_digits[3:]}"
        else:
            phone_number = existing_phone
        
        # Update the guest with email, password, and phone_number
        cur.execute("""
            UPDATE guests 
            SET email = ?, password = ?, phone_number = ? 
            WHERE guest_id = ?
        """, (email, common_password, phone_number, guest_id))
        
        updated_count += 1
        print(f"✅ {updated_count:2d}. {name:20s} | {email:30s} | {phone_number:18s}")
    
    # Commit changes
    conn.commit()
    
    print("=" * 90)
    print(f"\n✅ Updated {updated_count} guests with email, password, and phone number")
    print(f"📧 Email format: name@gmail.com")
    print(f"🔑 Common password: {common_password}")
    print(f"📱 Phone format: +91 XXXXX XXXXX (Indian numbers)")
    
    # Verify the update
    print("\n" + "=" * 90)
    print("Verification - First 10 guests:")
    print("=" * 90)
    cur.execute("SELECT guest_id, name, email, phone_number, password FROM guests LIMIT 10")
    for row in cur.fetchall():
        print(f"{row[0]} | {row[1]:15s} | {row[2]:25s} | {row[3]:18s} | {row[4]}")
    
    conn.close()
    print("\n✅ Population completed successfully!")

if __name__ == "__main__":
    try:
        populate_credentials()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
