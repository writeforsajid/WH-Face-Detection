from db.database import get_connection
from services.face_worker import process_guest_video_async
import random,datetime,os
from utilities.environment_variables import load_environment
import json
from typing import List, Dict
from fastapi import HTTPException
#from passlib.context import CryptContext
#import ffmpeg

#VIDEOS_PATH = "./data/videos"
load_environment("./../data/.env.webapp")
VIDEOS_PATH=os.getenv("VIDEOS_PATH","./../data/Videos")
STATIC_TEMP_PATH=os.getenv("STATIC_TEMP_PATH","./static/temp")
#pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
#VIDEOS_PATH = "./data/videos"



def create_guest(guest: dict):
  # ✅ Auto-generate Guest ID if not given

# Construct expected video filename
    guest_name_safe = guest["name"].replace(" ", "_")
    print(guest["name"])
    possible_files = [f for f in os.listdir(VIDEOS_PATH) if f.startswith(guest_name_safe)]
    
    if not possible_files:
        # No video uploaded yet
        return {"error": "Please capture and upload the video before saving the guest."}
   
    possible_files.sort(key=lambda f: os.path.getmtime(os.path.join(VIDEOS_PATH, f)), reverse=True)
    video_filename = possible_files[0]
    parts = video_filename.replace(".webm", "").split("_")
    guest_id = parts[-2] + parts[-1] if len(parts) == 3 else ""

    if not guest_id:
        return {"error": "Invalid video filename format. Expected two underscores in name."}

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM guests WHERE guest_id=?", (guest_id,))
    if cur.fetchone():
        conn.close()
        return {"error": "Guest already exists with this ID."}
    
    cur.execute("""
        INSERT INTO guests (guest_id, name, guest_type, bed_no, email, password, phone_number, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (guest_id, guest["name"], guest.get("guest_type"), guest["bed_no"],
          guest.get("email"), guest.get("password"), guest.get("phone_number"), 'active'))
 
    conn.commit()
    conn.close()
 
 
    # ✅ Start background processing
    process_guest_video_async(guest_id, guest["name"])

    return {"guest_id": guest_id, **guest,"message": "Guest saved! Face encoding in progress."}

def get_guests(page=1, limit=20, search: str | None = None, status: str | None = None):
    """
    Return paginated guests with optional filters:
      - search: case-insensitive substring match on name
      - status: one of ('active','inactive','closed')
    """
    offset = (page - 1) * limit
    conn = get_connection()
    cur = conn.cursor()

    where_clauses = []
    params: list = []

    if status:
        # Normalize and guard allowed values
        st = str(status).lower().strip()
        if st in ("active", "inactive", "closed"):
            where_clauses.append("LOWER(status) = ?")
            params.append(st)
    if search:
        where_clauses.append("LOWER(name) LIKE ?")
        params.append(f"%{str(search).lower().strip()}%")

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # total count with same filters
    cur.execute(f"SELECT COUNT(*) as cnt FROM guests{where_sql}", params)
    total = cur.fetchone()["cnt"]
    total_pages = (total + limit - 1) // limit if limit else 1

    cur.execute(
        f"SELECT * FROM guests{where_sql} ORDER BY name ASC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "items": rows,
    }


def get_bunch_of_beds():
    conn = get_connection()
    cur = conn.cursor()


    # ✅ Correct SQL syntax
    cur.execute("SELECT bed_id FROM beds ORDER BY bed_id")

    # Fetch all rows as list of strings
    rows = [row[0] for row in cur.fetchall()]
    conn.close()
    # Convert to JSON array
    bed_json = json.dumps(rows, indent=2)

    return bed_json
  

def delete_guest(guest_id: str):
    """
    Deletes a guest and all associated face records from the database.
    
    Args:
        guest_id (str): The unique ID of the guest to delete.
    
    Returns:
        bool: True if the guest was deleted successfully, False otherwise.
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        # 🧹 Step 1: Delete associated face encodings first (to maintain referential integrity)
        cur.execute("DELETE FROM guest_faces WHERE guest_id = ?", (guest_id,))

        # 🧹 Step 2: Now delete the guest record
        cur.execute("DELETE FROM guests WHERE guest_id = ?", (guest_id,))

        conn.commit()

        # 🧾 Step 3: Check if any guest record was deleted
        deleted = cur.rowcount > 0

    except Exception as e:
        conn.rollback()
        print(f"❌ Error deleting guest {guest_id}: {e}")
        deleted = False

    finally:
        conn.close()

    return deleted



def toggle_guest_status(guest_id: str):
    conn = get_connection()
    cur = conn.cursor()

    # Cycle through statuses: active -> inactive -> closed -> active
    cur.execute("""
        UPDATE guests
        SET status = CASE 
            WHEN status = 'active' THEN 'inactive'
            WHEN status = 'inactive' THEN 'closed'
            ELSE 'active'
        END
        WHERE guest_id = ?
    """, (guest_id,))
    
    conn.commit()
    cur.execute("SELECT guest_id, status FROM guests WHERE guest_id=?", (guest_id,))
    result = cur.fetchone()
    conn.close()

    if not result:
        return {"error": "Guest not found."}
    
    return {"guest_id": result[0], "status": result[1]}



def confirm_guest(guest_id: str):
    """
    Find the guest JSON file in VIDEOS_PATH and set 'confirmed' = True.
    Returns True if updated successfully, False if not found or failed.
    """
    try:
        filepath = os.path.join(VIDEOS_PATH, f"{guest_id}.json")
        print(f"❌ File Path: {filepath}")
        # Check if the file exists
        if not os.path.exists(filepath):
            print(f"❌ File not found for guest_id: {guest_id}")
            return False

        # Load JSON data
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Update confirmed status
        data["confirmed"] = True

        # Save back to the same file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ Guest {guest_id} confirmed successfully.")
        return True

    except Exception as e:
        print(f"⚠️ Error updating guest {guest_id}: {e}")
        return False


def get_guest_with_attendance(guest_id: str):
    """
    Fetch guest details along with their attendance records and bed assignment.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Get guest details
    cur.execute("""
        SELECT g.*, ga.bed_id, ga.assign_date
        FROM guests g
        LEFT JOIN guest_beds ga ON g.guest_id = ga.guest_id
        WHERE g.guest_id = ?
    """, (guest_id,))
    
    guest = cur.fetchone()
    
    if not guest:
        conn.close()
        return {"error": "Guest not found"}
    
    guest_data = dict(guest)
    
    # Get attendance records
    cur.execute("""
        SELECT * FROM attendance
        WHERE guest_id = ?
        ORDER BY timestamp DESC
    """, (guest_id,))
    
    attendance_records = [dict(r) for r in cur.fetchall()]
    conn.close()
    
    return {
        "guest": guest_data,
        "attendance": attendance_records
    }





async def change_password(guest_id,old_password, secret_key, new_password):

    conn = get_connection()
   
    # Example: fetch user row (replace 'guest' table and columns as per your schema)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT guest_id, password, phone_number FROM guest
        WHERE guest_id = ?
        ORDER BY timestamp DESC
    """, (guest_id,))
    
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    db_id, db_hashed_pw, db_secret_key = row

    # Check condition: either match old password OR secret key
    if old_password:
 #       if not pwd_context.verify(old_password, db_hashed_pw):
 #           raise HTTPException(status_code=401, detail="Old password incorrect")
 #   elif secret_key:
        if secret_key.upper() != db_secret_key.upper():
            raise HTTPException(status_code=401, detail="Secret key incorrect")
        # Hash and update password
#    new_hashed = pwd_context.hash(new_password)
#    cursor.execute("UPDATE guest SET password=? WHERE id=?", (new_hashed, db_id))
    conn.commit()
    conn.close()

    return "Password updated successfully"