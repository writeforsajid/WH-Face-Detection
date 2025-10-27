"""
Migration script to:
1. Add a 'status' column to the guests table with values: 'active', 'inactive', 'closed'
2. Populate 'status' with random values for all rows
3. Drop the old 'active' column (if present) while preserving full guests schema

Run this script once to update your database schema.
"""
import os
import sqlite3
from pathlib import Path


def migrate_guest_status():
    # Resolve DB path from env or default to ./../data/WhiteHouse.db relative to this file
    default_db = Path(__file__).parent.parent.parent / "data" / "WhiteHouse.db"
    db_path = Path(os.getenv("DB_PATH", str(default_db)))

    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    try:
        # Check if guests table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guests'")
        if not cur.fetchone():
            print("❌ Guests table does not exist")
            return False

        # Inspect current columns in guests table
        cur.execute("PRAGMA table_info(guests)")
        cols_info = cur.fetchall()
        columns = {row[1]: row for row in cols_info}

        has_active = "active" in columns
        has_status = "status" in columns

        print(f"📊 Current schema - has 'active': {has_active}, has 'status': {has_status}")

        # Step 1: Add status column if it doesn't exist (with CHECK constraint)
        if not has_status:
            print("📝 Adding 'status' column with CHECK constraint...")
            cur.execute(
                """
                ALTER TABLE guests
                ADD COLUMN status TEXT DEFAULT 'active'
                CHECK(status IN ('active','inactive','closed'))
                """
            )
            conn.commit()
            print("✅ Status column added")

        # Step 2: Populate status with random values for ALL rows
        print("🎲 Populating 'status' with random values (active/inactive/closed) for all rows...")
        cur.execute(
            """
            UPDATE guests
            SET status = CASE (ABS(RANDOM()) % 3)
                WHEN 0 THEN 'active'
                WHEN 1 THEN 'inactive'
                ELSE 'closed'
            END
            """
        )
        conn.commit()
        print("✅ Status randomized for all rows")

        # Step 3: If 'active' column exists, recreate table without it, preserving full schema
        if has_active:
            print("🧱 Removing legacy 'active' column while preserving full schema...")

            # Desired final guests schema (aligned with db.database.init_db)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS guests_new (
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
                """
            )

            # Determine common columns between old table and new target table (exclude 'active')
            target_cols = [
                "guest_id",
                "name",
                "email",
                "password",
                "phone",
                "phone_number",
                "bed_no",
                "guest_type",
                "status",
            ]
            # Refresh columns info after adding 'status' so we don't miss it
            cur.execute("PRAGMA table_info(guests)")
            cols_info_latest = cur.fetchall()
            existing_cols = [row[1] for row in cols_info_latest if row[1] != "active"]
            common = [c for c in target_cols if c in existing_cols]

            if not common:
                raise RuntimeError("No common columns found between existing 'guests' and target schema")

            cols_csv = ", ".join(common)
            print(f"➡️ Copying columns: {cols_csv}")

            cur.execute(f"INSERT INTO guests_new ({cols_csv}) SELECT {cols_csv} FROM guests")
            cur.execute("DROP TABLE guests")
            cur.execute("ALTER TABLE guests_new RENAME TO guests")
            conn.commit()
            print("✅ 'active' column removed and table recreated with full schema")

        # Verify the migration
        cur.execute("PRAGMA table_info(guests)")
        final_columns = [row[1] for row in cur.fetchall()]
        print("\n📊 Final schema columns:", final_columns)

        # Show status distribution
        cur.execute("SELECT status, COUNT(*) as count FROM guests GROUP BY status")
        print("\n📊 Status distribution:")
        for row in cur.fetchall():
            print(f"   {row[0]}: {row[1]} guests")

        print("\n✅ Migration completed successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("🚀 Starting migration: Add 'status' field, randomize values, and remove 'active' column from guests table\n")
    migrate_guest_status()
