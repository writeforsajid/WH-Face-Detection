"""
    (_venv) PS D:\Working\AI\WH Face Detection>python .\webapp\db\dbscript.py
    (_venv) PS D:\Working\AI\WH Face Detection\webapp> uvicorn main:app --reload --host 127.0.0.1 --port 8000 --ssl-keyfile="webapp.key" --ssl-certfile="webapp.crt"
Note: this file references the original uploaded file path: /mnt/data/dbscript.py for reference but does not import it. It uses same environment loader and crypto_manager used in original.
"""

import sqlite3
import json
import os
from pathlib import Path

# environment loader
from environment_variables import load_environment

# paths
DB_PATH = "./data/WhiteHouse.db"
script_dir = os.path.dirname(__file__)
load_environment("./../../data/.env.webapp")

# ensure folder exists
Path(os.path.join(script_dir, "dbscript_data")).mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# enforce foreign keys in sqlite
cursor.execute("PRAGMA foreign_keys = ON;")

print("🌱 Running RENT System Seeder...")



# ==========================
# CLEAR OLD DUMMY DATA
# ==========================
cursor.executescript("""
DROP Table IF EXISTS rent_payment_attachments;
DROP Table IF EXISTS rent_payment_allocations;
DROP Table IF EXISTS rent_forward_history;
DROP Table IF EXISTS rent_approval_history;
DROP Table IF EXISTS rent_payments;
DROP Table IF EXISTS security_deposits;
DROP Table IF EXISTS rent_change_events;
DROP Table IF EXISTS dues;
DROP Table IF EXISTS due_types;
""")
# ==========================
# CREATE TABLES
# ==========================
cursor.executescript("""

CREATE TABLE IF NOT EXISTS due_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,    -- e.g. RENT, ADVANCE, SECURITY, MAINT, ELEC, FOOD, REG, FINE, OTHER
    name TEXT NOT NULL            -- Human readable name
);

CREATE TABLE IF NOT EXISTS dues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id TEXT,                         -- keep as TEXT FK reference to guests(guest_id) if guests table exists
    due_type_id INTEGER REFERENCES due_types(id),
    year INTEGER,
    month INTEGER,
    due_amount REAL NOT NULL,
    amount_paid REAL DEFAULT 0,
    status TEXT DEFAULT 'open' CHECK (status IN ('open','partial','paid','adjusted')),
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE (guest_id, due_type_id, year, month)
);

CREATE TABLE IF NOT EXISTS rent_payments (
    rent_payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_by TEXT,
    guest_id TEXT,
    year INTEGER,
    month INTEGER,
    amount REAL NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('UPI','CASH','IMPS','DD')),
    reference TEXT,
    description TEXT,
    status TEXT DEFAULT 'submitted' CHECK (
        status IN ('submitted','forwarded','approved_final','rejected','cancelled')
    ),
    current_approver TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    approved_at TEXT,
    approved_by TEXT,
    final_receipt_url TEXT
);

-- Correct single allocations table (references dues.id)
CREATE TABLE IF NOT EXISTS rent_payment_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rent_payment_id INTEGER REFERENCES rent_payments(rent_payment_id) ON DELETE CASCADE,
    due_id INTEGER REFERENCES dues(id) ON DELETE SET NULL,
    allocated_amount REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS rent_payment_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rent_payment_id INTEGER REFERENCES rent_payments(rent_payment_id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    filename TEXT,
    uploaded_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rent_forward_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rent_payment_id INTEGER REFERENCES rent_payments(rent_payment_id) ON DELETE CASCADE,
    from_user TEXT,
    to_user TEXT,
    comment TEXT,
    forwarded_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rent_approval_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rent_payment_id INTEGER REFERENCES rent_payments(rent_payment_id) ON DELETE CASCADE,
    acted_by TEXT,
    action TEXT NOT NULL CHECK (action IN ('approved','rejected')),
    comment TEXT,
    acted_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS security_deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id TEXT,
    amount REAL NOT NULL,
    collected_on TEXT,
    refunded_amount REAL DEFAULT 0,
    refunded_on TEXT
);

CREATE TABLE IF NOT EXISTS rent_change_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id TEXT,
    old_rent REAL,
    new_rent REAL,
    changed_by TEXT,
    changed_at TEXT DEFAULT (datetime('now')),
    reason TEXT
);

CREATE TABLE IF NOT EXISTS rent_payment_refunds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id TEXT NOT NULL,
    due_id INTEGER REFERENCES dues(id),
    amount REAL NOT NULL,
    payment_mode TEXT DEFAULT 'UPI',
    reference TEXT,
    refunded_on DATE DEFAULT CURRENT_DATE,
    created_at TEXT DEFAULT (datetime('now'))
);

""")

print("✔ Tables created")

# ==========================
# INDEXES (RENT SYSTEM)
# ==========================
# Improved indexes for common queries
indexes = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_due_types_code ON due_types(code);

CREATE INDEX IF NOT EXISTS idx_dues_guest_year_month ON dues(guest_id, year, month);
CREATE INDEX IF NOT EXISTS idx_dues_guest_due_type ON dues(guest_id, due_type_id);
CREATE INDEX IF NOT EXISTS idx_dues_type_year_month ON dues(due_type_id, year, month);
CREATE INDEX IF NOT EXISTS idx_dues_guest_date ON dues (guest_id, created_at);


CREATE INDEX IF NOT EXISTS idx_rentpayments_guest ON rent_payments(guest_id);
CREATE INDEX IF NOT EXISTS idx_rentpayments_status ON rent_payments(status);
CREATE INDEX IF NOT EXISTS idx_rentpayments_year_month ON rent_payments(year, month);

CREATE INDEX IF NOT EXISTS idx_alloc_rentpayment_id ON rent_payment_allocations(rent_payment_id);
CREATE INDEX IF NOT EXISTS idx_alloc_due_id ON rent_payment_allocations(due_id);

CREATE INDEX IF NOT EXISTS idx_attach_rpid ON rent_payment_attachments(rent_payment_id);

CREATE INDEX IF NOT EXISTS idx_forward_rpid ON rent_forward_history(rent_payment_id);
CREATE INDEX IF NOT EXISTS idx_approval_rpid ON rent_approval_history(rent_payment_id);

CREATE INDEX IF NOT EXISTS idx_security_guest ON security_deposits(guest_id);
CREATE INDEX IF NOT EXISTS idx_rent_change_guest ON rent_change_events(guest_id);

"""
cursor.executescript(indexes)
print("✔ Indexes created/updated")

# ==========================
# CLEAR OLD DUMMY DATA
# ==========================
cursor.executescript("""
DELETE FROM rent_payment_attachments;
DELETE FROM rent_payment_allocations;
DELETE FROM rent_forward_history;
DELETE FROM rent_approval_history;
DELETE FROM rent_payments;
DELETE FROM dues;
DELETE FROM due_types;
DELETE FROM security_deposits;
DELETE FROM rent_change_events;
""")
print("✔ Old data cleared (tables truncated)")

# ==========================
# LOAD JSON DUMMY DATA
# ==========================
json_files = {
    "due_types.json": "due_types",
    "dues.json": "dues",
    "rent_payments.json": "rent_payments",
    "rent_payment_allocations.json": "rent_payment_allocations",
    "rent_payment_attachments.json": "rent_payment_attachments",
    "rent_forward_history.json": "rent_forward_history",
    "rent_approval_history.json": "rent_approval_history",
    "security_deposits.json": "security_deposits",
    "rent_change_events.json": "rent_change_events",
    # optional: "guests.json": "guests"  (if you have guests table)
}

for fname, table_name in json_files.items():
    path = os.path.join(script_dir, "dbscript_data", fname)
    if not os.path.exists(path):
        print(f"  - Skipping {fname} (file not found). Create {path} to seed {table_name}.")
        continue

    with open(path, "r", encoding="utf-8") as f:
        data_list = json.load(f)

    if not data_list:
        continue

    # auto-detect columns except 'id' if present
    cols = [c for c in data_list[0].keys() if c != "id"]
    columns = ", ".join(cols)
    placeholders = ", ".join(["?" for _ in cols])

    values = []
    for row in data_list:
        values.append(tuple(row.get(c) for c in cols))
    print(f"⏳ Inserting {len(data_list)} rows into {table_name} from {fname}...")
    cursor.executemany(
        f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
        values
    )
    conn.commit()
    print(f"✔ Inserted {len(values)} rows into {table_name} from {fname}")

conn.commit()
conn.close()

print("\n🎉 Seeder completed successfully!")
