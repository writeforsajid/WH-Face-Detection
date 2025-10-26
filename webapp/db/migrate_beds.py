"""
Quick migration script to ensure beds and guest_beds tables exist with correct schema.
Run this once to fix the database schema.
"""
import sqlite3
import os
import sys

# Change to webapp directory so relative paths work
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from db.database import get_connection

def migrate():
    conn = get_connection()
    cur = conn.cursor()
    
    print("Checking current schema...")
    
    # Check if beds table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='beds'")
    beds_exists = cur.fetchone()
    
    if beds_exists:
        # Check if it has the correct schema
        cur.execute("PRAGMA table_info(beds)")
        columns = {row[1] for row in cur.fetchall()}
        
        if 'bed_id' not in columns:
            print("❌ beds table exists but has wrong schema. Dropping and recreating...")
            cur.execute("DROP TABLE IF EXISTS guest_beds")
            cur.execute("DROP TABLE IF EXISTS beds")
        else:
            print("✅ beds table has correct schema")
    
    # Create beds table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS beds (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        bed_id    TEXT NOT NULL UNIQUE,
        description TEXT
    )
    """)
    print("✅ beds table created/verified")
    
    # Create guest_beds table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guest_beds (
        assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        guest_id      TEXT NOT NULL,
        bed_id      TEXT NOT NULL,
        assign_date   DATE DEFAULT (DATE('now')),
        FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON UPDATE CASCADE ON DELETE CASCADE,
        FOREIGN KEY (bed_id) REFERENCES beds(bed_id) ON UPDATE CASCADE
    )
    """)
    print("✅ guest_beds table created/verified")
    
    # Seed beds
    cur.execute("SELECT COUNT(*) FROM beds")
    bed_count = cur.fetchone()[0]
    
    if bed_count < 83:
        if bed_count > 0:
            print(f"Clearing existing {bed_count} beds to reseed with 83...")
            cur.execute("DELETE FROM guest_beds")
            cur.execute("DELETE FROM beds")
        
        print("Seeding 83 beds...")
        beds_data = []
        
        # Generate 83 beds across multiple rooms and floors
        # Pattern: Room 001-020, each with floor 1-2, each with bed 1-3 = flexible distribution
        bed_patterns = [
            # Room 001-010 (30 beds: 10 rooms × 3 beds)
            *[(f"{room:03d}/1/{bed}", f"Room {room:03d} Floor 1 - Bed {bed}") 
              for room in range(1, 11) for bed in range(1, 4)],
            
            # Room 011-020 (30 beds: 10 rooms × 3 beds)
            *[(f"{room:03d}/1/{bed}", f"Room {room:03d} Floor 1 - Bed {bed}") 
              for room in range(11, 21) for bed in range(1, 4)],
            
            # Room 101-108 with 2 floors (16 beds: 8 rooms × 2 beds on floor 1)
            *[(f"{room:03d}/1/{bed}", f"Room {room:03d} Floor 1 - Bed {bed}") 
              for room in range(101, 109) for bed in range(1, 3)],
            
            # Room 201-203 with 2 beds each (6 beds)
            *[(f"{room:03d}/1/{bed}", f"Room {room:03d} Floor 1 - Bed {bed}") 
              for room in range(201, 204) for bed in range(1, 3)],
            
            # Single bed rooms 301 (1 bed)
            ("301/1/1", "Room 301 Floor 1 - Bed 1"),
        ]
        
        beds_data = bed_patterns[:83]  # Take exactly 83 beds
        
        cur.executemany(
            "INSERT INTO beds (bed_id, description) VALUES (?, ?)",
            beds_data
        )
        print(f"✅ Seeded {len(beds_data)} beds")
    else:
        print(f"✅ Beds already seeded ({bed_count} beds)")
    
    # Seed guest_beds with sample data
    cur.execute("SELECT COUNT(*) FROM guest_beds")
    assignment_count = cur.fetchone()[0]
    
    if assignment_count == 0:
        print("Seeding guest bed assignments for all 83 beds...")
        
        # Get all guests
        cur.execute("SELECT guest_id FROM guests")
        guest_ids = [r[0] for r in cur.fetchall()]
        
        # Get all bed names
        cur.execute("SELECT bed_id FROM beds ORDER BY bed_id")
        all_beds = [r[0] for r in cur.fetchall()]
        
        if len(guest_ids) > 0 and len(all_beds) > 0:
            assignments = []
            
            # Assign guests to beds (cycle through guests if more beds than guests)
            for i, bed_id in enumerate(all_beds):
                guest_id = guest_ids[i % len(guest_ids)]  # Cycle through guests
                # Vary the assign dates slightly
                day = 1 + (i % 20)  # Days 1-20
                assign_date = f"2025-10-{day:02d}"
                assignments.append((guest_id, bed_id, assign_date))
            
            if assignments:
                cur.executemany(
                    "INSERT INTO guest_beds (guest_id, bed_id, assign_date) VALUES (?, ?, ?)",
                    assignments
                )
                print(f"✅ Seeded {len(assignments)} guest bed assignments")
        else:
            print(f"⚠️ Need guests and beds: found {len(guest_ids)} guests, {len(all_beds)} beds")
    else:
        print(f"✅ Assignments already exist ({assignment_count} assignments)")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migration complete! Restart your server.")

if __name__ == "__main__":
    migrate()
