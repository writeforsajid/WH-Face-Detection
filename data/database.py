import sqlite3
import os

def get_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'WhiteHouse.db')
    return sqlite3.connect(db_path)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Guests Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guests (
        guest_id    VARCHAR(20) PRIMARY KEY,
        name        VARCHAR(100) NOT NULL,
        email       TEXT,
        password    TEXT,
        phone_number TEXT,
        comments      VARCHAR(10),
        status      VARCHAR(20) DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'closed','leave'))
    )
    """)

    # Guest Faces Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guest_faces (
        face_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        guest_id    VARCHAR(20) NOT NULL,
        encoding    TEXT NOT NULL,
        added_on    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (guest_id) REFERENCES guests(guest_id)
    )
    """)

    # Attendance Table
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

    # Devices Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        device_id   VARCHAR(50) PRIMARY KEY,
        type        VARCHAR(20) CHECK(type IN ('RFID','Camera')),
        location    VARCHAR(100)
    )
    """)

    # Beds Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS beds (
        id      INTEGER       PRIMARY KEY AUTOINCREMENT,
        bed_id    VARCHAR (10)  NOT NULL,
        description VARCHAR (150)
    )
    """)

    # Guest Beds Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guest_beds (
        assignment_id INTEGER      PRIMARY KEY AUTOINCREMENT,
        guest_id      VARCHAR (20) NOT NULL,
        bed_id       VARCHAR (10) NOT NULL,
        assign_date   DATE         NOT NULL DEFAULT (DATE('now')),
        FOREIGN KEY (guest_id) REFERENCES guests (guest_id) ON UPDATE CASCADE ON DELETE CASCADE
    )
    """)

    # Guest Auth Table
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

    # Guest Sessions Table
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

    # Guest Password Resets Table
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

    # Roles Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        role_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        role_name  TEXT NOT NULL UNIQUE,
        priority   INTEGER NOT NULL
    )
    """)

    # Indices
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_guest_auth_email ON guest_auth(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_sessions_guest ON guest_sessions(guest_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_pwresets_guest ON guest_password_resets(guest_id)")

    # Seed roles
    cursor.executemany(
        "INSERT OR IGNORE INTO roles (role_name, priority) VALUES (?, ?)",
        [
            ("residence", 1),
            ("employee", 2),
            ("owner", 3),
        ]
    )

    conn.commit()
    conn.close()