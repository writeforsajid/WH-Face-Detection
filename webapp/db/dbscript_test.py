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


def insert_midnight_data():
    print("Running midnight job...")
    #conn = get_connection()
    #cur = conn.cursor()
    try:
        cursor.execute("""
            Select g.guest_id,b.sharing_type,b.bed_id,brp.monthly_rent,status from guests as a
            JOIN guest_roles AS g ON a.guest_id = g.guest_id
            Left join roles as r ON r.role_id = g.role_id
            Left join guest_beds as gb ON gb.guest_id = g.guest_id
            Left join beds as b ON b.bed_id= gb.bed_id
            Left join bed_rent_plan as brp ON brp.sharing_type = b.sharing_type
            where status <>'closed' and r.role_name ='resident'     
        """)

        rows = cursor.fetchall()
        today = datetime.today()
        # Extract the year and month
        current_year = today.year
        current_month = today.month

        for r in rows:
            guest_id      = r[0]
            # sharing_type  = r[1]
            # bed_id        = r[2]
            # monthly_rent  = r[3]    # <-- IMPORTANT FIX
            # status        = r[4]
            calculated_rent = r[3] or 0
            guest_id = r[0]
            if calculated_rent < 0:
                calculated_rent = 6000  # Default rent if not found
            # Insert due record
            cursor.execute(f"""
                INSERT INTO dues (guest_id, year, month, due_type_id, due_amount)
                SELECT '{guest_id}', {current_year}, {current_month}, 1, {calculated_rent}
                WHERE NOT EXISTS (
                    SELECT 1 FROM dues m
                    WHERE m.guest_id = '{guest_id}'
                    AND m.year = {current_year}
                    AND m.month = {current_month}
                );
            """)
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()

    print("Job completed.")





if __name__ == "__main__":
    load_environment("./../data/.env.yolocam")
    insert_midnight_data()

print(f"✅ Database created at: {DB_PATH}")


