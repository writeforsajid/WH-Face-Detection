import sqlite3
from datetime import datetime
import face_recognition 
import json
import os
from pathlib import Path
# Connect (creates file WhiteHouse.db if not exists)
conn = sqlite3.connect("./data/WhiteHouse.db")
cursor = conn.cursor()

# 1️⃣ Guests Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS guests (
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


# 4️⃣ Guest Faces Table (NEW)
cursor.execute("""
CREATE TABLE IF NOT EXISTS guest_faces (
    face_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id    VARCHAR(20) NOT NULL,
    encoding    TEXT NOT NULL,   -- JSON string of 128-dim face encoding
    added_on    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id)
)
""")


# 2️⃣ Attendance Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id    VARCHAR(20) NOT NULL,
    method      VARCHAR(20) CHECK(method IN ('RFID','Face','Manual')),
    device_id   VARCHAR(50),
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced      BOOLEAN DEFAULT 0,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id)
)
""")

# 3️⃣ Devices Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS devices (
    device_id   VARCHAR(50) PRIMARY KEY,
    type        VARCHAR(20) CHECK(type IN ('RFID','Camera')),
    location    VARCHAR(100)
)
""")

# 3️⃣ Devices Table
cursor.execute("""
CREATE TABLE beds (
    id      INTEGER       PRIMARY KEY AUTOINCREMENT,
    bed_id    VARCHAR (10)  NOT NULL,
    description VARCHAR (150) 
)
""")


# 3️⃣ guest_metadata Table
cursor.execute("""
CREATE TABLE guest_metadata (
    meta_id     INTEGER       PRIMARY KEY AUTOINCREMENT,
    guest_id    VARCHAR (20)  NOT NULL,
    name        VARCHAR (20)  NOT NULL,
    description VARCHAR (150),
    created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (
        guest_id
    )
    REFERENCES guests (guest_id) ON UPDATE CASCADE
                                 ON DELETE CASCADE
)
""")


# 3️⃣ guest_beds Table
cursor.execute("""
CREATE TABLE guest_beds (
    assignment_id INTEGER      PRIMARY KEY AUTOINCREMENT,
    guest_id      VARCHAR (20) NOT NULL,
    bed_id       VARCHAR (10) NOT NULL,
    assign_date   DATE         NOT NULL
                               DEFAULT (DATE('now') ),
    FOREIGN KEY (
        guest_id
    )
    REFERENCES guests (guest_id) ON UPDATE CASCADE
                                 ON DELETE CASCADE
)
""")

# 8️⃣ Authentication: Guest-based auth tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS guest_auth (
    guest_id    VARCHAR(20) PRIMARY KEY,
    email       TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    is_active   BOOLEAN DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE
)
""")

# 9️⃣ Guest Sessions table
cursor.execute("""
CREATE TABLE IF NOT EXISTS guest_sessions (
    session_id  TEXT PRIMARY KEY,
    guest_id    VARCHAR(20) NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at  TIMESTAMP,
    user_agent  TEXT,
    ip_address  TEXT,
    revoked     BOOLEAN DEFAULT 0,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE
)
""")

# 🔟 Guest Password resets table
cursor.execute("""
CREATE TABLE IF NOT EXISTS guest_password_resets (
    token       TEXT PRIMARY KEY,
    guest_id    VARCHAR(20) NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at  TIMESTAMP NOT NULL,
    used        BOOLEAN DEFAULT 0,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE
)
""")

# Indices
cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_guest_auth_email ON guest_auth(email)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_sessions_guest ON guest_sessions(guest_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_pwresets_guest ON guest_password_resets(guest_id)")

# 1️⃣1️⃣ Roles tables and seeding
cursor.execute("""
CREATE TABLE IF NOT EXISTS roles (
    role_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name  TEXT NOT NULL UNIQUE,
    priority   INTEGER NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS guest_roles (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id   VARCHAR(20) NOT NULL UNIQUE,
    role_id    INTEGER NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE RESTRICT
)
""")

cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_roles_name ON roles(role_name)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_roles_guest ON guest_roles(guest_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_roles_role ON guest_roles(role_id)")

# Seed default roles (priority: owner=1, residence=2, employee=3)
cursor.executemany(
    "INSERT OR IGNORE INTO roles (role_name, priority) VALUES (?, ?)",
    [
        ("owner", 1),
        ("employee", 2),
        ("residence", 3),
    ]
)

# 7️⃣ Insert Dummy Beds
beds = [
    ("001/1/1", "Floor 0 Flat 1 Room 1 Bed 1"),
    ("001/1/2", "Floor 0 Flat 1 Room 1 Bed 2"),
    ("001/1/3", "Floor 0 Flat 1 Room 1 Bed 3"),
    ("002/1/1", "Floor 0 Flat 2 Room 1 Bed 1"),
    ("002/1/2", "Floor 0 Flat 2 Room 1 Bed 2"),
    ("002/1/3", "Floor 0 Flat 2 Room 1 Bed 3"),
    ("002/1/2", "Floor 0 Flat 2 Room 2 Bed 1"),
    ("002/2/2", "Floor 0 Flat 2 Room 2 Bed 1"),
    ("002/2/2", "Floor 0 Flat 2 Room 2 Bed 2"),
    ("002/2/3", "Floor 0 Flat 2 Room 2 Bed 3"),
    ("103/1/1", "Floor 1 Flat 3 Room 1 Bed 1"),
    ("103/1/2", "Floor 1 Flat 3 Room 1 Bed 2"),
    ("103/2/1", "Floor 1 Flat 3 Room 2 Bed 1"),
    ("103/2/2", "Floor 1 Flat 3 Room 2 Bed 2"),
    ("103/2/3", "Floor 1 Flat 3 Room 2 Bed 3"),
    ("104/1/1", "Floor 1 Flat 4 Room 1 Bed 1"),
    ("104/1/2", "Floor 1 Flat 4 Room 1 Bed 2"),
    ("104/2/1", "Floor 1 Flat 4 Room 2 Bed 1"),
    ("104/2/2", "Floor 1 Flat 4 Room 2 Bed 2"),
    ("104/2/3", "Floor 1 Flat 4 Room 2 Bed 3"),
    ("203/1/1", "Floor 2 Flat 3 Room 1 Bed 1"),
    ("203/1/2", "Floor 2 Flat 3 Room 1 Bed 2"),
    ("203/2/1", "Floor 2 Flat 3 Room 2 Bed 1"),
    ("203/2/2", "Floor 2 Flat 3 Room 2 Bed 2"),
    ("203/2/3", "Floor 2 Flat 3 Room 2 Bed 3"),
    ("204/1/1", "Floor 2 Flat 4 Room 1 Bed 1"),
    ("204/1/2", "Floor 2 Flat 4 Room 1 Bed 2"),
    ("204/2/1", "Floor 2 Flat 4 Room 2 Bed 1"),
    ("204/2/2", "Floor 2 Flat 4 Room 2 Bed 2"),
    ("204/2/3", "Floor 2 Flat 4 Room 2 Bed 3"),
    ("303/1/1", "Floor 3 Flat 3 Room 1 Bed 1"),
    ("303/1/2", "Floor 3 Flat 3 Room 1 Bed 2"),
    ("303/2/1", "Floor 3 Flat 3 Room 2 Bed 1"),
    ("303/2/2", "Floor 3 Flat 3 Room 2 Bed 2"),
    ("303/2/3", "Floor 3 Flat 3 Room 2 Bed 3"),
    ("304/1/1", "Floor 3 Flat 4 Room 1 Bed 1"),
    ("304/1/2", "Floor 3 Flat 4 Room 1 Bed 2"),
    ("304/2/1", "Floor 3 Flat 4 Room 2 Bed 1"),
    ("304/2/2", "Floor 3 Flat 4 Room 2 Bed 2"),
    ("304/2/3", "Floor 3 Flat 4 Room 2 Bed 3"),
    ("401/1/1", "Floor 4 Flat 1 Room 1 Bed 1"),
    ("401/1/2", "Floor 4 Flat 1 Room 1 Bed 2"),
    ("401/1/3", "Floor 4 Flat 1 Room 1 Bed 3"),
    ("401/2/1", "Floor 4 Flat 1 Room 2 Bed 1"),
    ("401/2/2", "Floor 4 Flat 1 Room 2 Bed 2"),
    ("401/2/3", "Floor 4 Flat 1 Room 2 Bed 3"),
    ("402/1/1", "Floor 4 Flat 2 Room 1 Bed 1"),
    ("402/1/2", "Floor 4 Flat 2 Room 1 Bed 2"),
    ("402/1/3", "Floor 4 Flat 2 Room 1 Bed 3"),
    ("402/2/1", "Floor 4 Flat 2 Room 2 Bed 1"),
    ("402/2/2", "Floor 4 Flat 2 Room 2 Bed 2"),
    ("402/2/3", "Floor 4 Flat 2 Room 2 Bed 3"),
    ("403/1/1", "Floor 4 Flat 3 Room 1 Bed 1"),
    ("403/1/2", "Floor 4 Flat 3 Room 1 Bed 2"),
    ("403/2/1", "Floor 4 Flat 3 Room 2 Bed 1"),
    ("403/2/2", "Floor 4 Flat 3 Room 2 Bed 2"),
    ("403/2/3", "Floor 4 Flat 3 Room 2 Bed 3"),
    ("404/1/1", "Floor 4 Flat 4 Room 1 Bed 1"),
    ("404/1/2", "Floor 4 Flat 4 Room 1 Bed 2"),
    ("404/2/1", "Floor 4 Flat 4 Room 2 Bed 1"),
    ("404/2/2", "Floor 4 Flat 4 Room 2 Bed 2"),
    ("404/2/3", "Floor 4 Flat 4 Room 2 Bed 3"),
    ("501/1/1", "Floor 5 Flat 1 Room 1 Bed 1"),
    ("501/1/2", "Floor 5 Flat 1 Room 1 Bed 2"),
    ("501/1/3", "Floor 5 Flat 1 Room 1 Bed 3"),
    ("501/2/1", "Floor 5 Flat 1 Room 2 Bed 1"),
    ("501/2/2", "Floor 5 Flat 1 Room 2 Bed 2"),
    ("501/2/3", "Floor 5 Flat 1 Room 2 Bed 3"),
    ("502/1/1", "Floor 5 Flat 2 Room 1 Bed 1"),
    ("502/1/2", "Floor 5 Flat 2 Room 1 Bed 2"),
    ("502/1/3", "Floor 5 Flat 2 Room 1 Bed 3"),
    ("502/2/1", "Floor 5 Flat 2 Room 2 Bed 1"),
    ("502/2/2", "Floor 5 Flat 2 Room 2 Bed 2"),
    ("502/2/3", "Floor 5 Flat 2 Room 2 Bed 3"),
    ("503/1/1", "Floor 5 Flat 3 Room 1 Bed 1"),
    ("503/1/2", "Floor 5 Flat 3 Room 1 Bed 2"),
    ("503/2/1", "Floor 5 Flat 3 Room 2 Bed 1"),
    ("503/2/2", "Floor 5 Flat 3 Room 2 Bed 2"),
    ("503/2/3", "Floor 5 Flat 3 Room 2 Bed 3"),
    ("504/1/1", "Floor 5 Flat 4 Room 1 Bed 1"),
    ("504/1/2", "Floor 5 Flat 4 Room 1 Bed 2"),
    ("504/2/1", "Floor 5 Flat 4 Room 2 Bed 1"),
    ("504/2/2", "Floor 5 Flat 4 Room 2 Bed 2"),
    ("504/2/3", "Floor 5 Flat 4 Room 2 Bed 3"),
]


cursor.executemany(
    "INSERT OR IGNORE INTO beds (bed_id, description) VALUES (?, ?)",
    beds
)

# 5️⃣ Insert Dummy Guests
guests = [
    ("20250001000001", "unknown", "Resident", "000",  1),
    ("20250105000001", "Shiza", "Resident", "101",  1),
    ("20250210000002", "Sajid", "Employee", "102",  1),
    ("20250301000003", "Nurpara", "Employee", "103",  1),
    ("20250301000004", "Arish", "Resident", "104",  1),
    ("20250301000005", "Ashmat", "Resident", "105",  1),
    ("20250301000006", "Majid", "Employee", "106",  1),
    ("20250301000007", "Runa", "Employee", "107",  1),
    ("20250301000008", "Nasreen", "Employee", "108",  1),
    ("20250301000009", "Nazim", "Employee", "109",  1),
    ("20250301000010", "Faizia", "Resident", "108",  1)
]
cursor.executemany("INSERT OR IGNORE INTO guests VALUES (?,?,?,?,?)", guests)

# 6️⃣ Insert Dummy Devices
devices = [
    ("RFID01", "RFID", "Main Gate"),
    ("CAM01", "Camera", "Dining Hall"),
    ("OUT", "Camera", "Out"),
    ("IN", "Camera", "In")        
]
cursor.executemany("INSERT OR IGNORE INTO devices VALUES (?,?,?)", devices)

# 7️⃣ Insert Dummy Attendance
attendance = [
    ("20250105000001", "RFID", "RFID01", "2025-09-16 20:15:00", 1),
    ("20250105000001", "Face", "CAM01", "2025-09-16 20:16:05", 1),
    ("20250210000002", "Manual", "ADMIN01", "2025-09-16 20:30:00", 0),
    ("20250301000003", "RFID", "RFID01", "2025-09-16 21:05:00", 1)
]
cursor.executemany("INSERT INTO attendance (guest_id, method, device_id, timestamp, synced) VALUES (?,?,?,?,?)", attendance)



# Insert dummy metadata
guest_metadata = [
    ("20250105000001", "VIP", "Frequent guest, prefers top floor rooms."),
    ("20250105000001", "LongTerm", "Resident since 2023, extended stay guest."),
    ("20250105000001", "Staff", "Employee - Security Department."),
    ("20250105000001", "Visitor", "Occasional visitor, friend of resident."),
    ("20250105000001", "Maintenance", "Assigned to facility maintenance."),
]
cursor.executemany(
    "INSERT OR IGNORE INTO guest_metadata (guest_id, name, description) VALUES (?, ?, ?)",
    guest_metadata
)

# Insert dummy bed assignments
guest_beds = [
    ("20250105000001", "100/1/1", "2025-10-01"),
    ("20250105000001", "100/1/2", "2025-10-02"),
    ("20250105000001", "200/1/1", "2025-09-25"),
    ("20250105000001", "200/1/2", "2025-10-10"),
    ("20250105000001", "201/1/1", "2025-10-12")
]
cursor.executemany(
    "INSERT OR IGNORE INTO guest_beds (guest_id, bed_id, assign_date) VALUES (?, ?, ?)",
    guest_beds
)


# 8️⃣ Insert Dummy Guest Faces (fake encodings for demo)
# Normally you’d store json.dumps(face_encoding.tolist())
# ----------------------------
# Known faces folder
# ----------------------------
BASE_DIR = Path(__file__).resolve().parent
KNOWN_DIR = BASE_DIR / "..//..//../images"   # Folder: images/Alice/*.jpg, images/Bob/*.jpg

# ----------------------------
# Loop through folders
# ----------------------------
for person_dir in KNOWN_DIR.iterdir():
    if not person_dir.is_dir():
        continue

    guest_id = person_dir.name  # folder name = guest_id
    print(f"[INFO] Processing {guest_id}...")

    for img_path in person_dir.glob("*.jpg"):
        # Load image
        img = face_recognition.load_image_file(str(img_path))
        encs = face_recognition.face_encodings(img)

        if len(encs) == 0:
            print(f"[WARNING] No face found in {img_path}")
            continue

        encoding = encs[0]
        encoding_json = json.dumps(encoding.tolist())  # save as JSON string

        # Insert into DB
        cursor.execute(
            "INSERT INTO guest_faces (guest_id, encoding) VALUES (?, ?)",
            (guest_id, encoding_json)
        )

# Commit & Close
conn.commit()
conn.close()

print("✅ WhiteHouse.db created/updated with guests, attendance, devices, guest_faces, guest_auth, guest_sessions, guest_password_resets, roles, guest_roles tables!")
