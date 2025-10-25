import sqlite3
import os
from utilities.environment_variables import load_environment
DB_PATH = "./../data/WhiteHouse.db"
load_environment("./../data/.env.webapp")


def get_connection():
    # # ✅ get current app directory (this file's folder)
    # app_dir = os.path.dirname(os.path.abspath(__file__))

    # # ✅ construct absolute path to .env.webapp
    # env_path = os.path.join(app_dir, "../data/WhiteHouse.db")

    # # ✅ normalize to absolute path
    # env_path = os.path.abspath(env_path)

    DB_PATH=os.getenv("DB_PATH","./../data/WhiteHouse.db")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # returns rows as dict-like objects
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    
    # Create tables if not exist
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guests (
        guest_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT,
        password TEXT,
        phone TEXT,
        phone_number TEXT,
        bed_no TEXT,
        guest_type TEXT DEFAULT 'Resident' CHECK(guest_type IN ('Owner', 'Employee', 'Resident', 'Others')),
        status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'closed'))
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guest_id TEXT,
        method TEXT,
        device_id TEXT,
        timestamp TEXT,
        synced INTEGER DEFAULT 0,
        FOREIGN KEY (guest_id) REFERENCES guests(guest_id)
    )
    """)

    # Beds master table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS beds (
        bed_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        bed_name    TEXT NOT NULL UNIQUE,
        description TEXT
    )
    """)

    # Guest bed assignments table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guest_beds (
        assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        guest_id      TEXT NOT NULL,
        bed_name      TEXT NOT NULL,
        assign_date   DATE DEFAULT (DATE('now')),
        FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON UPDATE CASCADE ON DELETE CASCADE,
        FOREIGN KEY (bed_name) REFERENCES beds(bed_name) ON UPDATE CASCADE
    )
    """)

    # Authentication tables (guest-based login)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guest_auth (
        guest_id TEXT PRIMARY KEY,
        email TEXT UNIQUE,
        password_hash TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS guest_sessions (
        session_id TEXT PRIMARY KEY,
        guest_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        user_agent TEXT,
        ip_address TEXT,
        revoked INTEGER DEFAULT 0,
        FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS guest_password_resets (
        token TEXT PRIMARY KEY,
        guest_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        used INTEGER DEFAULT 0,
        FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE
    )
    """)

    # Helpful indexes
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_guest_auth_email ON guest_auth(email)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_guest_sessions_guest ON guest_sessions(guest_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_guest_pwresets_guest ON guest_password_resets(guest_id)")

    # Roles core table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        role_id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_name TEXT NOT NULL UNIQUE,
        priority INTEGER NOT NULL
    )
    """)

    # Link roles to guests (one role per guest)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS guest_roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guest_id TEXT NOT NULL UNIQUE,
        role_id INTEGER NOT NULL,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE,
        FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE RESTRICT
    )
    """)

    # Indexes for roles
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_roles_name ON roles(role_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_guest_roles_guest ON guest_roles(guest_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_guest_roles_role ON guest_roles(role_id)")

    # Seed default roles with priority: 1 owner, 2 residence, 3 employee
    cur.executemany(
        "INSERT OR IGNORE INTO roles (role_name, priority) VALUES (?, ?)",
        [
            ("owner", 1),  
            ("employee", 2),
            ("residence", 3),
        ],
    )

    # Seed beds if table is empty
    cur.execute("SELECT COUNT(*) FROM beds")
    row = cur.fetchone()
    bed_count = row[0] if row else 0
    if bed_count == 0:
        beds_data = []
        
        # Generate 83 beds across multiple rooms and floors
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
            "INSERT INTO beds (bed_name, description) VALUES (?, ?)",
            beds_data
        )

    # Seed guest_beds with sample data (only if table is empty)
    cur.execute("SELECT COUNT(*) FROM guest_beds")
    row = cur.fetchone()
    assignment_count = row[0] if row else 0
    if assignment_count == 0:
        # Get all guests
        cur.execute("SELECT guest_id FROM guests")
        guest_ids = [r[0] for r in cur.fetchall()]
        
        # Get all bed names
        cur.execute("SELECT bed_name FROM beds ORDER BY bed_name")
        all_beds = [r[0] for r in cur.fetchall()]
        
        if len(guest_ids) > 0 and len(all_beds) > 0:
            assignments = []
            
            # Assign guests to beds (cycle through guests if more beds than guests)
            for i, bed_name in enumerate(all_beds):
                guest_id = guest_ids[i % len(guest_ids)]  # Cycle through guests
                # Vary the assign dates slightly
                day = 1 + (i % 20)  # Days 1-20
                assign_date = f"2025-10-{day:02d}"
                assignments.append((guest_id, bed_name, assign_date))
            
            if assignments:
                cur.executemany(
                    "INSERT INTO guest_beds (guest_id, bed_name, assign_date) VALUES (?, ?, ?)",
                    assignments
                )
    
    conn.commit()
    conn.close()
