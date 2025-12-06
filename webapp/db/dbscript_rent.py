"""
(_venv) PS D:\Working\AI\WH Face Detection>python .\webapp\db\dbscript.py
Note: this file references the original uploaded file path: /mnt/data/dbscript.py for reference but does not import it. It uses same environment loader and crypto_manager used in original.
"""


import sqlite3
import json
import os
from pathlib import Path
import random
from datetime import datetime, timedelta

from environment_variables import load_environment
# Connect (creates file WhiteHouse.db if not exists)
DB_PATH = "./data/WhiteHouse_Fresh.db"
script_dir = os.path.dirname(__file__)
load_environment("./../../data/.env.webapp")

#if os.path.exists(DB_PATH):
#    os.remove(DB_PATH)


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("🌱 Running RENT System Seeder...")

# ==========================
# CREATE TABLES
# ==========================

cursor.executescript("""
CREATE TABLE IF NOT EXISTS monthly_rent_dues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id TEXT REFERENCES guests(guest_id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    due_amount REAL NOT NULL,
    amount_paid REAL DEFAULT 0,
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'partial', 'paid', 'adjusted')),
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE (guest_id, year, month)
);


CREATE TABLE IF NOT EXISTS rent_payments (
    rent_payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_by TEXT REFERENCES guests(guest_id),
    guest_id TEXT REFERENCES guests(guest_id),
    year INTEGER,
    month INTEGER,
    amount REAL NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('UPI','CASH','IMPS','DD')),
    reference TEXT,
    description TEXT,
    status TEXT DEFAULT 'submitted' CHECK (
        status IN ('submitted','forwarded','approved_final','rejected','cancelled')
    ),
    current_approver TEXT REFERENCES guests(guest_id),
    created_at TEXT DEFAULT (datetime('now')),
    approved_at TEXT,
    approved_by TEXT REFERENCES guests(guest_id),
    final_receipt_url TEXT
);

CREATE TABLE IF NOT EXISTS rent_payment_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rent_payment_id INTEGER REFERENCES rent_payments(rent_payment_id) ON DELETE CASCADE,
    monthly_rent_due_id INTEGER REFERENCES monthly_rent_dues(id),
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
    from_user TEXT REFERENCES guests(guest_id),
    to_user TEXT REFERENCES guests(guest_id),
    comment TEXT,
    forwarded_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rent_approval_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rent_payment_id INTEGER REFERENCES rent_payments(rent_payment_id) ON DELETE CASCADE,
    acted_by TEXT REFERENCES guests(guest_id),
    action TEXT NOT NULL CHECK (action IN ('approved','rejected')),
    comment TEXT,
    acted_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rent_ledger_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rent_payment_id INTEGER REFERENCES rent_payments(rent_payment_id),
    guest_id TEXT REFERENCES guests(guest_id),
    amount REAL NOT NULL,
    entry_type TEXT CHECK (entry_type IN ('credit','debit')),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS security_deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id TEXT REFERENCES guests(guest_id),
    amount REAL NOT NULL,
    collected_on TEXT,
    refunded_amount REAL DEFAULT 0,
    refunded_on TEXT
);

CREATE TABLE IF NOT EXISTS rent_change_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id TEXT REFERENCES guests(guest_id),
    old_rent REAL,
    new_rent REAL,
    changed_by TEXT REFERENCES guests(guest_id),
    changed_at TEXT DEFAULT (datetime('now')),
    reason TEXT
);

""")

print("✔ Tables created")



# ========== INDEXES (RENT SYSTEM) ==========

# cursor.execute("""CREATE INDEX IF NOT EXISTS idx_monthly_dues_gid_ym 
# ON monthly_dues(guest_id, year, month);""")

# cursor.execute("""CREATE INDEX IF NOT EXISTS idx_rent_guest 
# ON rents(guest_id);""")

# cursor.execute("""CREATE INDEX IF NOT EXISTS idx_rent_approver 
# ON rents(current_approver);""")

# cursor.execute("""CREATE INDEX IF NOT EXISTS idx_rent_year_month 
# ON rents(year, month);""")

indexes = """
CREATE INDEX IF NOT EXISTS idx_rent_guest ON rent_payments(guest_id);
CREATE INDEX IF NOT EXISTS idx_monthly_dues_gid_yr_m ON monthly_rent_dues(guest_id, year, month);
CREATE INDEX IF NOT EXISTS idx_rent_current_approver ON rent_payments(current_approver);
CREATE INDEX IF NOT EXISTS idx_rent_alloc_rpid ON rent_payment_allocations(rent_payment_id);
CREATE INDEX IF NOT EXISTS idx_rent_attach_rpid ON rent_payment_attachments(rent_payment_id);
CREATE INDEX IF NOT EXISTS idx_rent_ledger_guest ON rent_ledger_entries(guest_id);
CREATE INDEX IF NOT EXISTS idx_security_guest ON security_deposits(guest_id);
CREATE INDEX IF NOT EXISTS idx_rent_change_guest ON rent_change_events(guest_id);
"""
cursor.executescript(indexes)

# ==========================
# CLEAR OLD DUMMY DATA
# ==========================

cursor.executescript("""
DELETE FROM rent_payments;
DELETE FROM rent_payment_allocations;
DELETE FROM rent_payment_attachments;
DELETE FROM rent_forward_history;
DELETE FROM rent_approval_history;
DELETE FROM rent_ledger_entries;
DELETE FROM rent_change_events;
DELETE FROM security_deposits;
DELETE FROM monthly_rent_dues;
""")
print("✔ Old data cleared")
# ==========================================
# DUMMY DATA FOR RENT MODULE
# ==========================================



json_file_path = os.path.join(script_dir, 'dbscript_data', 'guests.json')
# List of JSON files and corresponding tables
json_to_table = {
    "monthly_rent_dues.json": "monthly_rent_dues",
    "rent_payments.json": "rent_payments",
    "rent_payment_allocations.json": "rent_payment_allocations",
    "rent_payment_attachments.json": "rent_payment_attachments",
    "rent_forward_history.json": "rent_forward_history",
    "rent_approval_history.json": "rent_approval_history",
    "rent_ledger_entries.json": "rent_ledger_entries"
}

for json_file, table_name in json_to_table.items():
    print(f"Inserting data for {table_name} from {json_file}...")
    json_file_path = os.path.join(script_dir, 'dbscript_data', json_file)

    with open(f"{json_file_path}", "r", encoding="utf-8") as f:
        data_list = json.load(f)
    
    if not data_list:
        continue
    #data = load_json(json_path)
# Detect columns except id

    # auto-detect columns except 'id'
    cols = [c for c in data_list[0].keys() if c != "id"]

    columns = ", ".join(cols)
    placeholders = ", ".join(["?" for _ in cols])

    values = []
    for row in data_list:
        values.append(tuple(row[c] for c in cols))
    
    # Insert data
    cursor.executemany(
        f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})",
        values
    )
    conn.commit()

print("✔ All JSON data inserted successfully!")
# ==========================
# COMMIT & CLOSE
# ==========================

conn.commit()
conn.close()

print("\n🎉 Seeder completed successfully!")
