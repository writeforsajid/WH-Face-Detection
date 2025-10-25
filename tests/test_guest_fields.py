"""
Quick test to verify the new guest fields are working correctly.
"""
import sys
import os

# Add webapp to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'webapp'))

from db.database import get_connection

def test_guest_fields():
    """Test that new fields exist in guests table"""
    conn = get_connection()
    cur = conn.cursor()
    
    print("Testing guest table schema...")
    
    # Check table schema
    cur.execute("PRAGMA table_info(guests)")
    columns = {row[1]: row[2] for row in cur.fetchall()}
    
    required_fields = ['email', 'password', 'phone_number']
    
    print("\n✅ Checking for required fields:")
    all_present = True
    for field in required_fields:
        if field in columns:
            print(f"  ✅ {field} ({columns[field]})")
        else:
            print(f"  ❌ {field} - NOT FOUND")
            all_present = False
    
    if all_present:
        print("\n🎉 All required fields are present in the guests table!")
    else:
        print("\n❌ Some fields are missing. Please run the migration script.")
    
    # Test inserting a guest with new fields
    print("\n" + "="*60)
    print("Testing guest insertion with new fields...")
    
    test_guest_id = "TEST_" + str(int(os.times()[4] * 1000000))
    
    try:
        cur.execute("""
            INSERT INTO guests (guest_id, name, email, password, phone_number, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        """, (test_guest_id, "Test User", "test@example.com", "testpass123", "+1234567890"))
        
        conn.commit()
        
        # Verify insertion
        cur.execute("SELECT guest_id, name, email, password, phone_number FROM guests WHERE guest_id = ?", (test_guest_id,))
        row = cur.fetchone()
        
        if row:
            print("✅ Guest inserted successfully:")
            print(f"  - Guest ID: {row[0]}")
            print(f"  - Name: {row[1]}")
            print(f"  - Email: {row[2]}")
            print(f"  - Password: {row[3]}")
            print(f"  - Phone Number: {row[4]}")
            
            # Clean up test data
            cur.execute("DELETE FROM guests WHERE guest_id = ?", (test_guest_id,))
            conn.commit()
            print("\n✅ Test data cleaned up")
        else:
            print("❌ Failed to insert guest")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        conn.rollback()
    
    finally:
        conn.close()
    
    print("\n" + "="*60)
    print("Test completed!")

if __name__ == "__main__":
    test_guest_fields()
