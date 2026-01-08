"""
(_venv) PS D:\Working\AI\WH Face Detection>python .\webapp\db\dbscript.py
Note: this file references the original uploaded file path: /mnt/data/dbscript.py for reference but does not import it. It uses same environment loader and crypto_manager used in original.
"""
# TODO: Script dbscript_leave

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


cursor.execute('''
CREATE TABLE IF NOT EXISTS leave_types (
    leave_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_paid INTEGER DEFAULT 1 -- boolean: 0/1
);
''')


cursor.execute('''
CREATE UNIQUE INDEX IF NOT EXISTS idx_leave_types_name ON leave_types(name);
''')


#-- 2) leave_requests (guest-applied leaves; admins can also create)
cursor.execute('''
CREATE TABLE IF NOT EXISTS leave_requests (
    leave_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id TEXT NOT NULL,
    leave_type_id INTEGER,
    start_date DATE NOT NULL,   -- use start_date/end_date columns
    end_date DATE NOT NULL,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'pending'  CHECK(status IN ('pending','approved','rejected','cancelled')),
    applied_on TEXT DEFAULT (datetime('now')),
    applied_by TEXT,         -- who applied (guest or admin user_id)
    approved_by TEXT,        -- user_id of approver (warden/owner)
    approved_on TEXT,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE,
    FOREIGN KEY (leave_type_id) REFERENCES leave_types(leave_type_id)
);
''')

cursor.execute('''CREATE INDEX IF NOT EXISTS idx_leave_requests_guest ON leave_requests(guest_id);''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_leave_requests_status ON leave_requests(status);''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_leave_requests_start_end ON leave_requests(start_date, end_date);''')

#-- 3) leave_calendar_cache (one row per guest + date for fast lookup)
cursor.execute('''
CREATE TABLE IF NOT EXISTS leave_calendar_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id TEXT NOT NULL,
    leave_date DATE NOT NULL,
    leave_id INTEGER NOT NULL,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE,
    FOREIGN KEY (leave_id) REFERENCES leave_requests(leave_id) ON DELETE CASCADE
);
''')



cursor.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_leave_cache_guest_date ON leave_calendar_cache(guest_id, leave_date);''')
cursor.execute('''CREATE UNIQUE INDEX IF NOT EXISTS idx_leave_cache_guest_date ON leave_calendar_cache(guest_id, leave_date);''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_leave_cache_leave_id ON leave_calendar_cache(leave_id);''')

#-- 4) attendance_alerts (keeps admin-informed about conflicts)
cursor.execute('''
CREATE TABLE IF NOT EXISTS attendance_alerts (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id TEXT NOT NULL,
    alert_date DATE NOT NULL,
    leave_id INTEGER,                 -- related leave if any
    attendance_id INTEGER,            -- related attendance row if any
    message TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    handled INTEGER DEFAULT 0,        -- 0 = new, 1 = acknowledged/handled
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id),
    FOREIGN KEY (leave_id) REFERENCES leave_requests(leave_id),
    FOREIGN KEY (attendance_id) REFERENCES attendance(id)
);
''')

cursor.execute('''
CREATE INDEX IF NOT EXISTS idx_att_alerts_guest_date ON attendance_alerts(guest_id, alert_date);
''')

#-- 5) Trigger: When a leave is APPROVED -> populate leave_calendar_cache (expand dates)
#--    and when a leave is changed to non-approved (rejected/cancelled) remove those cache rows.
#-- Note: Uses WITH RECURSIVE to generate date range.
cursor.execute('''
CREATE TRIGGER IF NOT EXISTS trg_leave_requests_after_approve
AFTER UPDATE OF status ON leave_requests
WHEN NEW.status = 'approved'
BEGIN
    DELETE FROM leave_calendar_cache WHERE leave_id = NEW.leave_id;

    INSERT INTO leave_calendar_cache (guest_id, leave_date, leave_id)
    WITH RECURSIVE seq(day) AS (
        SELECT date(NEW.start_date)
        UNION ALL
        SELECT date(day, '+1 day') FROM seq WHERE day < date(NEW.end_date)
    )
    SELECT NEW.guest_id, day, NEW.leave_id FROM seq;
END;
''')


cursor.execute('''
CREATE TRIGGER IF NOT EXISTS trg_leave_requests_after_unapprove
AFTER UPDATE OF status ON leave_requests
WHEN NEW.status IN ('rejected','cancelled') AND OLD.status = 'approved'
BEGIN
    DELETE FROM leave_calendar_cache WHERE leave_id = NEW.leave_id;
END;
''')


#-- 6) Trigger: If an attendance record is inserted for a date where an approved leave exists:
#--    create an attendance_alerts row (we still keep attendance row, we DO NOT delete it).
#--    This covers the rule: "Mark Present but also Alert admin".
cursor.execute('''
CREATE TRIGGER IF NOT EXISTS trg_attendance_insert_check_leave_conflict
AFTER INSERT ON attendance
WHEN EXISTS (
    SELECT 1 FROM leave_calendar_cache lc
    WHERE lc.guest_id = NEW.guest_id
      AND lc.leave_date = date(NEW.timestamp)
)
BEGIN
    INSERT INTO attendance_alerts(guest_id, alert_date, leave_id, attendance_id, message)
    SELECT NEW.guest_id,
           date(NEW.timestamp),
           lc.leave_id,
           NEW.id,
           'Attendance present during approved leave - guest punched and will be marked Present; notify admin'
    FROM leave_calendar_cache lc
    WHERE lc.guest_id = NEW.guest_id
      AND lc.leave_date = date(NEW.timestamp)
    LIMIT 1;
END;
''')


#-- 7) Optional: If a leave is approved that overlaps existing attendance rows, raise alerts.
#--    This handles the situation where leave is approved after attendance already exists for those days.
cursor.execute('''
CREATE TRIGGER IF NOT EXISTS trg_leave_approve_detect_existing_attendance
AFTER UPDATE OF status ON leave_requests
WHEN NEW.status = 'approved'
BEGIN
    INSERT INTO attendance_alerts(guest_id, alert_date, leave_id, attendance_id, message)
    WITH RECURSIVE seq(day) AS (
        SELECT date(NEW.start_date)
        UNION ALL
        SELECT date(day, '+1 day') FROM seq WHERE day < date(NEW.end_date)
    )
    SELECT a.guest_id,
           date(a.timestamp),
           NEW.leave_id,
           a.id,
           'Existing attendance found for date on which leave was approved - notify admin'
    FROM attendance a
    JOIN seq ON date(a.timestamp) = seq.day
    WHERE a.guest_id = NEW.guest_id;
END;
''')

#-- 8) Ensure indexes on attendance for quick lookups by date

cursor.execute('''CREATE INDEX IF NOT EXISTS idx_attendance_guest_date ON attendance(guest_id, date(timestamp));''')

leave_types = [
    ("Home Visit", "Staying at home for a few days"),
    ("Personal Leave", "General purpose leave"),
    ("Medical Leave", "Health-related leave"),
    ("Outing", "Going out for short duration")
]

cursor.executemany("INSERT INTO leave_types (name, description) VALUES (?,?)", leave_types)

"""
-- 9) A recommended view-like query (we will supply as a SELECT template) to get attendance status for a date.
--    Note: SQLite views are static; we'll provide a parameterized SELECT you can use from app/backend.
--    Replace :target_date with your date (e.g., '2025-11-26').

-- Query template to get status for all guests for a given date:
-- The logic: 
--   If guest has an attendance row (any timestamp) for that date => Present
--   Else if guest has leave_calendar_cache row for that date => Leave
--   Else => Absent

-- Example usage (replace :target_date with actual date string):
/*
SELECT 
  g.guest_id,
  g.name,
  CASE 
    WHEN a.att_timestamp IS NOT NULL THEN 'Present'
    WHEN lc.leave_date IS NOT NULL THEN 'Leave'
    ELSE 'Absent'
  END AS status,
  a.att_timestamp,
  lc.leave_date
FROM guests g
LEFT JOIN (
  -- latest attendance timestamp for guest on that date (or any attendance row)
  SELECT guest_id, max(timestamp) AS att_timestamp
  FROM attendance
  WHERE date(timestamp) = :target_date
  GROUP BY guest_id
) a ON a.guest_id = g.guest_id
LEFT JOIN (
  SELECT guest_id, leave_date FROM leave_calendar_cache WHERE leave_date = :target_date
) lc ON lc.guest_id = g.guest_id
ORDER BY g.name;
*/

-- 10) Utility: Admin-only backdated leave policy enforcement should be implemented at application layer:
--     only allow users with role (warden/owner) to insert leave_requests with start_date < date('now').
--     But we can add a trigger to flag such rows (optional).
"""


# Commit & Close
conn.commit()
conn.close()

print(f"✅ Database created at: {DB_PATH}")


