"""


(_venv) PS D:\Working\AI\WH Face Detection>python .\webapp\db\dbscript.py
(_venv) PS D:\Working\AI\WH Face Detection\webapp> uvicorn main:app --reload --host 127.0.0.1 --port 8000 --ssl-keyfile="webapp.key" --ssl-certfile="webapp.crt"

Enhanced SQLite DB script for WhiteHouse project
- Builds on the uploaded dbscript.py (path: /mnt/data/dbscript.py)
- Adds Payment Collection schema (bed_rent_plan, rent_monthly, rent_transactions, payment_screenshots)
- Keeps original tables (guests, beds, attendance, devices, roles, guest_roles, guest_auth, guest_sessions, guest_password_resets, guest_beds, guest_metadata, guest_faces)
- Preserves pattern used in original dbscript.py (hardcoded inserts, crypto usage, env loader)
- SQLite only. Local screenshot storage (Option A) supported.
- Seeds larger dummy data set (keeps existing entries and appends generated entries up to ~120 guests)

Run: python dbscript_payment_sqlite.py

Note: this file references the original uploaded file path: /mnt/data/dbscript.py for reference but does not import it. It uses same environment loader and crypto_manager used in original.
"""
# TODO: Script dbscript

import sqlite3
import face_recognition 
import json
import os
from pathlib import Path
import random
from datetime import datetime, timedelta
import subprocess

from environment_variables import load_environment
# Connect (creates file WhiteHouse.db if not exists)
DB_PATH = "./data/WhiteHouse_Fresh.db"
script_dir = os.path.dirname(__file__)
load_environment("./../../data/.env.webapp")
from crypto_manager import crypto
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)



conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1️⃣ Guests Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS guests (
    guest_id    VARCHAR(20) PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    email       TEXT UNIQUE,
    phone_number TEXT,
    comments      VARCHAR(100),
    status      VARCHAR(10) DEFAULT 'null' CHECK(status IN ('_blank','inactive','active',  'closed')),
    email_enabled INTEGER DEFAULT 1
)
""")

# 2 Guest Faces Table (NEW)
cursor.execute("""
CREATE TABLE guest_profile (
    guest_id          INTEGER       NOT NULL,
    date_of_birth     DATE,
    phone_number      VARCHAR (10),
    emergency_contact VARCHAR (10),
    permanent_address TEXT,
    pincode           VARCHAR (6),
    police_station    VARCHAR (100),
    aadhaar_number    VARCHAR (12),
    marital_status    VARCHAR (10),
    created_at        DATETIME      DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME      DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (
        guest_id
    ),
    FOREIGN KEY (
        guest_id
    )
    REFERENCES guests (guest_id) ON DELETE CASCADE
                                 ON UPDATE CASCADE
);
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
    sharing_type VARCHAR (10) NOT NULL,               
    description VARCHAR (150)
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







cursor.execute("""
CREATE TABLE appconfig (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(20) NOT NULL,
    description JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")






# 1️⃣1️⃣ Roles tables and seeding
cursor.execute("""
CREATE TABLE IF NOT EXISTS roles (
    role_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name  TEXT NOT NULL UNIQUE,
    priority   INTEGER NOT NULL
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS bed_rent_plan (
    plan_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    sharing_type  TEXT NOT NULL UNIQUE,
    monthly_rent  INTEGER NOT NULL,     -- stored in paise
    currency      TEXT DEFAULT 'INR'
);
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





cursor.execute('''CREATE TABLE guest_metadata (
    meta_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id    VARCHAR(20) NOT NULL,
    name        VARCHAR(20) NOT NULL,
    description VARCHAR(150),
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id TEXT,
    email_to TEXT NOT NULL,
    email_cc TEXT,
    email_bcc TEXT,
    subject TEXT,
    template_name TEXT,
    status TEXT CHECK(status IN ('SUCCESS','FAILED')) NOT NULL,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)''')




# cursor.execute('''
# CREATE TABLE IF NOT EXISTS leave_types (
#     leave_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT NOT NULL UNIQUE,                -- e.g., Sick Leave, Casual Leave
#     description TEXT,
#     is_paid BOOLEAN DEFAULT 1
# )
# ''')

# cursor.execute('''
# CREATE TABLE IF NOT EXISTS leave_requests (
#     leave_id INTEGER PRIMARY KEY AUTOINCREMENT,
#     guest_id TEXT NOT NULL,
#     leave_type_id INTEGER NOT NULL,
#     start_date DATE NOT NULL,
#     end_date DATE NOT NULL,
#     reason TEXT,
#     status TEXT NOT NULL DEFAULT 'pending' 
#         CHECK(status IN ('pending','approved','rejected','cancelled')),
#     applied_on TEXT DEFAULT (datetime('now')),
#     approved_by INTEGER,  -- user_id (admin/warden)
#     approved_on TEXT,
#     FOREIGN KEY (guest_id) REFERENCES guests(guest_id),
#     FOREIGN KEY (leave_type_id) REFERENCES leave_types(leave_type_id)
# )
# ''')

# cursor.execute('''
# CREATE TABLE IF NOT EXISTS leave_calendar_cache (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     guest_id TEXT NOT NULL,
#     leave_date DATE NOT NULL,
#     leave_id INTEGER NOT NULL,
#     FOREIGN KEY (guest_id) REFERENCES guests(guest_id),
#     FOREIGN KEY (leave_id) REFERENCES leave_requests(leave_id)
# )
# ''')









#-- 5) Trigger: When a leave is APPROVED -> populate leave_calendar_cache (expand dates)
#--    and when a leave is changed to non-approved (rejected/cancelled) remove those cache rows.
#-- Note: Uses WITH RECURSIVE to generate date range.
cursor.execute('''
CREATE TRIGGER limit_guest_faces
BEFORE INSERT ON guest_faces
WHEN (
    SELECT COUNT(*) FROM guest_faces WHERE guest_id = NEW.guest_id
) >= 3
BEGIN
    SELECT RAISE(ABORT, 'Maximum 3 encodings allowed per guest');
END;
''')












cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_roles_name ON roles(role_name)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_roles_guest ON guest_roles(guest_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_roles_role ON guest_roles(role_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guests_status ON guests(status)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guests_name ON guests(name COLLATE NOCASE)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_gr_guest_id ON guest_roles(guest_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_gr_role_id ON guest_roles(role_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_roles_role_id ON roles(role_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_gb_guest_id ON guest_beds(guest_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_gb_bed_id ON guest_beds(bed_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_beds_bed_id ON beds(bed_id)")

cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_guest_email ON guests(email)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_sessions_guest ON guest_sessions(guest_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_pwresets_guest ON guest_password_resets(guest_id)")

# ---------------------------
# Final indexing (performance)
# ---------------------------
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_phone ON guests(phone_number)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_guest_time ON attendance(guest_id, timestamp)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_beds_guest ON guest_beds(guest_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_beds_sharing ON beds(sharing_type)")


# cursor.execute("CREATE INDEX IF NOT EXISTS idx_pay_guest ON payments(guest_id);")
# cursor.execute("CREATE INDEX IF NOT EXISTS idx_montly_dues_gidyrmm ON  monthly_dues(guest_id, year, month);")
# cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_approver ON payments(current_approver);")
# cursor.execute("CREATE INDEX IF NOT EXISTS idx_payment_allocations_pid ON payment_allocations(payment_id);")


# cursor.execute("CREATE INDEX IF NOT EXISTS idx_leave_requests_guest ON leave_requests(guest_id);")
# cursor.execute("CREATE INDEX IF NOT EXISTS idx_leave_requests_dates ON leave_requests(start_date, end_date);")
# cursor.execute("CREATE INDEX IF NOT EXISTS idx_leave_requests_status ON leave_requests(status);")
# cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_leave_types_name ON leave_types(name);")
# cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_leave_cache_guest_date ON leave_calendar_cache(guest_id, leave_date);")
# cursor.execute("CREATE INDEX IF NOT EXISTS idx_leave_cache_leave_id ON leave_calendar_cache(leave_id);")





# Seed default roles (priority: owner=1, resident=2, employee=3)
cursor.executemany(
    "INSERT OR IGNORE INTO roles (role_name, priority) VALUES (?, ?)",
    [
        ("resident", 1),
        ("employee", 2),
        ("owner", 3),
    ]
)



# ---------------------------
# Seed bed_rent_plan (example prices)
# ---------------------------
plans = [
    ("brass", 6000.00),
    ("silver", 7000.00),
    ("golden", 8000.00)
]
cursor.executemany("INSERT OR IGNORE INTO bed_rent_plan (sharing_type, monthly_rent) VALUES (?, ?)", plans)



# --- JSON you want to save ---
description_data = {
    'options': [
    {'value': 'registered', 'label': 'registered'}, 
    {'value': 'bed assigned', 'label': 'bed assigned'}, 
    {'value': 'paid by', 'label': 'paid by'}, 
    {'value': 'police verify#', 'label': 'police verify#'}, 
    {'value': 'Mango', 'label': 'Mango'}, 
    {'value': 'Pineapple', 'label': 'Pineapple'}, 
    {'value': 'Watermelon', 'label': 'Watermelon'}, 
    {'value': 'Strawberry', 'label': 'Strawberry'}, 
    {'value': 'Papaya', 'label': 'Papaya'}, 
    {'value': 'Kiwi', 'label': 'Kiwi'}]
    }

# Convert Python dict to JSON string
description_json = json.dumps(description_data)

# --- Insert into table ---
cursor.execute("""
    INSERT INTO appconfig (name, description)
    VALUES (?, ?)
""", ("LOG_ITEMS", description_json))
cursor.execute("""
    INSERT INTO appconfig (name, description)
    VALUES (?, ?)
""", ("EMAIL_NOTIFICATION", 'on'))





json_file_path = os.path.join(script_dir, 'dbscript_data', 'guests.json')
# Load JSON
with open(json_file_path, "r") as f:
    guest_data = json.load(f)

# Convert to tuple list
guests = [(g["guest_id"], g["name"], g["email"], g["phone"]) for g in guest_data]

# Insert into SQLite
cursor.executemany(
    """
    INSERT OR IGNORE INTO guests 
    (guest_id, name, email,  phone_number, comments, status)
    VALUES (?, ?, ?,  ?, '', 'active')
    """,
    guests
)





json_file_path = os.path.join(script_dir, 'dbscript_data', 'beds.json')

# Load JSON file
with open(json_file_path, "r") as f:
    bed_data = json.load(f)

# Convert into list of tuples
beds = [(item["bed_id"],item["sharing_type"] ,item["description"]) for item in bed_data]

cursor.executemany(
    "INSERT OR IGNORE INTO beds (bed_id, sharing_type,description) VALUES (?,?, ?)",
    beds
)



# ---------------------------
# Seed bed_rent_plan (example prices)
# ---------------------------
plans = [
("brass", 6000.00),
("silver", 7000.00),
("golden", 8000.00)
]
cursor.executemany("INSERT OR IGNORE INTO bed_rent_plan (sharing_type, monthly_rent) VALUES (?, ?)", plans)
# 5️⃣ Insert Dummy Guests


#cursor.executemany("INSERT OR IGNORE INTO guests VALUES (?,?,?,'Pass@123',?,'','Resident',1)", guests)



# ---------------------------
# Create guest_auth entries for all guests (using crypto.encrypt similar to original)
# ---------------------------
all_guest_ids = [row[0] for row in cursor.execute("SELECT guest_id FROM guests").fetchall()]
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
for guest_id in all_guest_ids:
    password_hash = crypto.encrypt("Pass@123")
    cursor.execute(
        "INSERT OR REPLACE INTO guest_auth (guest_id, password_hash, is_active, created_at, updated_at) VALUES (?, ?, 1, ?, ?)",
        (guest_id, password_hash, now, now)
    )




# Useful indexes



json_file_path = os.path.join(script_dir, 'dbscript_data', 'guest_roles.json')
# Load JSON file
with open(json_file_path, "r") as f:
    data = json.load(f)

guest_roles = [
    (item["guest_id"], item["role_id"], item["assigned_at"])
    for item in data["guest_roles"]
]


cursor.executemany(
    "INSERT OR IGNORE INTO guest_roles (guest_id, role_id, assigned_at) VALUES (?, ?, ?)",
    guest_roles
)




# 6️⃣ Insert Dummy Devices
devices = [
    ("RFID01", "RFID", "Main Gate"),
    ("CAM01", "Camera", "Dining Hall"),
    ("EXIT_CAM", "Camera", "Out"),
    ("LIFT_CAM", "Camera", "In")        
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


json_file_path = os.path.join(script_dir, 'dbscript_data', 'guest_beds.json')

# Load JSON file
with open(json_file_path, "r") as f:
    data = json.load(f)

guest_beds = [
    (item["guest_id"], item["bed_id"], item["assign_date"])
    for item in data["guest_beds"]
]

# Insert into SQLite
cursor.executemany(
    "INSERT OR IGNORE INTO guest_beds (guest_id, bed_id, assign_date) VALUES (?, ?, ?)",
    guest_beds
)


# Path to your JSON file

json_file_path = os.path.join(script_dir, 'dbscript_data', 'guest_metadata.json')
# Read JSON data
with open(json_file_path, 'r') as f:
    guest_metadata = json.load(f)

# Insert data into table
cursor.executemany(
    "INSERT OR IGNORE INTO guest_metadata (guest_id, name, description, timestamp) VALUES (?, ?, ?, ?)",
    [(row['guest_id'], row['name'], row['description'], row['timestamp']) for row in guest_metadata]
)




def generate_attendance_records(start_date: str, end_date: str, total_records: int = 3000):
    """
    Generate random attendance data between start_date and end_date.
    Example: start_date='2025-01-01', end_date='2025-01-30'
    """

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    delta_days = (end_dt - start_dt).days
    records = []

    for _ in range(total_records):
        # Random guest_id in given range
        guest_id = f"20250105{random.randint(1,83):06d}"

        # Random day within range
        random_day = start_dt + timedelta(days=random.randint(0, delta_days))
        # Random time in the day
        random_time = timedelta(seconds=random.randint(0, 86399))
        timestamp = random_day + random_time
        hour = timestamp.hour

        # Decide device_id based on time logic
        if 18 <= hour <= 23:
            # 6 PM – 11 PM → mostly LIFT_CAM
            device_id = "LIFT_CAM" if random.random() < 0.95 else "EXIT_CAM"
        elif 6 <= hour < 18:
            # 6 AM – 6 PM → 50% EXIT_CAM
            device_id = "EXIT_CAM" if random.random() < 0.5 else "LIFT_CAM"
        else:
            # Late night or early morning (after 11 PM)
            # Small % appear — randomly assign
            device_id = random.choice(["EXIT_CAM", "LIFT_CAM"])

        records.append((guest_id, "Face", device_id, timestamp.isoformat(), 0))
    #cursor.execute("DELETE FROM attendance;")
    cursor.executemany(
        "INSERT INTO attendance (guest_id, method, device_id, timestamp, synced) VALUES (?,?,?,?,?)",
        records
    )


    print(f"✅ Inserted {total_records} random attendance records from {start_date} to {end_date}.")



########################################
generate_attendance_records(start_date="2025-09-01", end_date="2025-12-01", total_records=10000);
#######################################3






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
    print(f"[INFO] Processing (guest_id)...")

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


subprocess.Popen(["python", ".\webapp\db\dbscript_leave.py"])
subprocess.Popen(["python", ".\webapp\db\dbscript_rent.py"])

print(f"✅ Database created at: {DB_PATH}")
print("Tables: guests, beds, guest_beds, devices, attendance, roles, guest_roles, guest_auth, guest_sessions, guest_password_resets, guest_metadata, guest_faces, bed_rent_plan, rent_monthly, rent_transactions, payment_screenshots")
print("Dummy data: guests (~" + str(len(all_guest_ids)) + "), rent_monthly and transactions seeded for many guests.")
