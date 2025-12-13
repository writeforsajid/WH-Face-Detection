from db.database import get_connection
from services.face_worker import process_guest_video_async
import random,datetime,os
from utilities.environment_variables import load_environment
import json
from typing import List, Dict
from fastapi import HTTPException
import re
import os, shutil, json, zipfile
from datetime import datetime
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
        INSERT INTO guests (guest_id, name, comment, email, password, phone_number, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (guest_id, guest["name"],  guest["comment"],
          guest.get("email"), guest.get("password"), guest.get("phone_number"), 'active'))
 
    id = 1 if guest.get("guest_type").lower() == "resident" else 2 if guest.get("guest_type").lower() == "employee" else 3
    cur.execute("""
        INSERT OR IGNORE INTO guest_roles (guest_id, role_id,assigned_at) 
        VALUES (?,?, ?)
    """, (guest_id, id,datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    conn.commit()
    conn.close()
 
 
    # ✅ Start background processing
    process_guest_video_async(guest_id, guest["name"])

    return {"guest_id": guest_id, **guest,"message": "Guest saved! Face encoding in progress."}

def get_guests(page=1, limit=20, search: str | None = None, status: str | None = None):
    """
    Return paginated guests joined with role and bed info.
    Columns: guest_id, name, guest_type, bed_id, status
    Supports optional filters:
      - search: case-insensitive substring match on name
      - status: one of ('active','inactive','closed')
    """


    offset = (page - 1) * limit
    conn = get_connection()
    # conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Build WHERE filters dynamically
    # where_clauses = []
    where_clauses = ["LOWER(r.role_name) = 'resident'"]  # 👈 force only employees
    params = []
    
    if status:
        st = str(status).lower().strip()
        if st in ("active", "inactive", "closed"):
            where_clauses.append("LOWER(g.status) = ?")
            params.append(st)

    if search:
        where_clauses.append("LOWER(g.name) LIKE ?")
        params.append(f"%{search.lower().strip()}%")

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    # --- ⚡ Optimized query ---
    # Use LEFT JOIN to include guests even if role/bed missing
    # Use COALESCE for readable defaults
    base_query = f"""
        FROM guests AS g
        LEFT JOIN guest_roles AS gr ON g.guest_id = gr.guest_id
        LEFT JOIN roles AS r ON gr.role_id = r.role_id
        LEFT JOIN guest_beds AS gb ON g.guest_id = gb.guest_id
        LEFT JOIN beds AS b ON gb.bed_id = b.bed_id
        LEFT JOIN guest_faces AS gf ON g.guest_id = gf.guest_id   
        {where_sql}
    """

    # --- total count for pagination ---
    cur.execute(f"SELECT COUNT(DISTINCT g.guest_id) AS cnt {base_query}", params)
    total = cur.fetchone()["cnt"]
    total_pages = (total + limit - 1) // limit if limit else 1

    # --- main data query ---
    cur.execute(
        f"""
        SELECT 
            g.guest_id,
            g.name,
            g.email,
            COALESCE(b.bed_id, '-') AS bed_no,
            g.status,
            COUNT(gf.face_id) AS face_count
        {base_query}
        GROUP BY g.guest_id
        ORDER BY g.guest_id DESC
        LIMIT ? OFFSET ?
        """,
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
        cur.execute("DELETE FROM guest_auth WHERE guest_id = ?", (guest_id,))
        cur.execute("DELETE FROM guest_beds WHERE guest_id = ?", (guest_id,))
        cur.execute("DELETE FROM guest_faces WHERE guest_id = ?", (guest_id,))
        cur.execute("DELETE FROM guest_metadata WHERE guest_id = ?", (guest_id,))
        cur.execute("DELETE FROM guest_roles WHERE guest_id = ?", (guest_id,))
        cur.execute("DELETE FROM guest_sessions WHERE guest_id = ?", (guest_id,))
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
    # Cycle through statuses: active -> leave -> inactive -> closed -> active
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



# def confirm_guest(guest_id: str):
#     """
#     Find the guest JSON file in VIDEOS_PATH and set 'confirmed' = True.
#     Returns True if updated successfully, False if not found or failed.
#     """
#     try:
#         filepath = os.path.join(VIDEOS_PATH, f"{guest_id}.json")
        
#         # Check if the file exists
#         if not os.path.exists(filepath):
#             print(f"❌ File not found for guest_id: {guest_id}")
#             return False

#         # Load JSON data
#         with open(filepath, "r", encoding="utf-8") as f:
#             data = json.load(f)

#         # Update confirmed status
#         data["confirmed"] = True

#         # Save back to the same file
#         with open(filepath, "w", encoding="utf-8") as f:
#             json.dump(data, f, indent=2, ensure_ascii=False)

#         print(f"✅ Guest {guest_id} confirmed successfully.")
#         return True

#     except Exception as e:
#         print(f"⚠️ Error updating guest {guest_id}: {e}")
#         return False


def confirm_guest(guest_id: str) -> bool:
    """
    Find the guest JSON file in VIDEOS_PATH and set 'confirmed' = True.
    Returns True if updated successfully, False if not found or failed.
    """
    try:
        
        filepath = os.path.join(VIDEOS_PATH, f"{guest_id}.json")
        json_path = os.path.join(VIDEOS_PATH, f"{guest_id}.json")
        video_path = os.path.join(VIDEOS_PATH, f"{guest_id}.webm")
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
    # --- Create ZIP containing video + JSON ---
        
        zip_folder = os.path.join(VIDEOS_PATH, "ZIP")
        os.makedirs(zip_folder, exist_ok=True)   # Makes folder if not exists

        # Save zip in ZIP folder
        zip_filename = f"{guest_id}.zip"
        zip_path = os.path.join(zip_folder, zip_filename)

        # --- Create ZIP file ---
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(video_path, arcname=f"{guest_id}.webm")
            zipf.write(json_path, arcname=f"{guest_id}.json")
        return True
    
    except Exception as e:
        print(f"⚠️ Error updating guest {guest_id}: {e}")
        return False


def get_history_records(guest_id, start_date, end_date, page, limit):
    offset = (page - 1) * limit
    conn = get_connection()
    cur = conn.cursor()


    # Fetch paginated attendance
    query = """
        SELECT 
            a.meta_id,
            a.name,
            a.description,
            a.timestamp,
            g.guest_id
        FROM guest_metadata AS a
        JOIN guests AS g ON a.guest_id = g.guest_id
        WHERE a.guest_id = ?
          AND DATE(a.timestamp) BETWEEN ? AND ?
        ORDER BY a.timestamp DESC
        LIMIT ? OFFSET ?
    """
    cur.execute(query, (guest_id,start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), limit, offset))
    records = cur.fetchall()


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


    data = []
    for row in records:
        
        timestamp = row["timestamp"]
        if not isinstance(timestamp, str):
            timestamp = timestamp.strftime("%Y-%m-%d %I:%M %p")
        


        data.append({
            "id": row["meta_id"],
            "guest_id": row["guest_id"],
            "name": row["name"],
            "description": row["description"],
            "timestamp": row["timestamp"]
        })

    # Count total records for pagination
    count_query = """
        SELECT COUNT(*) AS total
        FROM guest_metadata
        WHERE guest_id = ? AND DATE(timestamp) BETWEEN ? AND ?
    """
    cur.execute(count_query, (guest_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
    total = cur.fetchone()["total"]

    conn.close()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": data,
        "guest": guest_data
    }



def get_guest_history(guest_id: str):
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
        SELECT * FROM guest_metadata
        WHERE guest_id = ?
        ORDER BY timestamp DESC
    """, (guest_id,))
    
    history_records = [dict(r) for r in cur.fetchall()]
    conn.close()
    
    return {
        "guest": guest_data,
        "history": history_records
    }

def add_guest_metadata(meta: dict):
    guest_id = meta.get("guest_id")
    name = meta.get("name")
    description = meta.get("description")
    timestamp = meta.get("timestamp")

    if not guest_id or not name:
        raise ValueError("guest_id and name are required.")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO guest_metadata (guest_id, name, description, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (guest_id, name, description, timestamp),
        )
        conn.commit()
        return{
                    "lastrowid": cur.lastrowid,
                    "status": 'success'
                }

    finally:
        conn.close()

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



def get_guest_ifemailexist(guest_email: str):
    """
    Fetch guest details along with their attendance records and bed assignment.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT guest_id FROM guests WHERE email = ?", (guest_email,))
    row = cur.fetchone()
    conn.close()

    return {"exists": row is not None}









def update_guest(meta: dict):

    try:
        guest_id = meta.get("guest_id")
        name = meta.get("name", "").strip()
        email = meta.get("email", "").strip()
        phone = meta.get("phone_number", "").strip()
        comments = meta.get("comments", "").strip()
        status = meta.get("status", "").strip()

        # === Validation ===
        if not all([guest_id, name, email, phone, comments, status]):
            return {"error": "All fields are required"}
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            return {"error": "Invalid email format"}
        if not phone.isdigit() or len(phone) != 10:
            return {"error": "Phone number must be 10 digits"}
        if status not in ['active', 'inactive', 'closed', 'leave']:
            return {"error": "Invalid status value"}

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE guests 
        SET name=?, email=?, phone_number=?, comments=?, status=? 
        WHERE guest_id=?
    """, (name, email, phone, comments, status, guest_id))
        conn.commit()
        conn.close()

        if cursor.rowcount == 0:
            return {"error": "Guest not found"}

        return {"success": True}

    except Exception as e:
        return {"error": str(e)}
    




def get_active_guests():
    conn = get_connection()
    cur = conn.cursor()
    query = """
        SELECT 
            g.guest_id as id,
            g.name
        FROM guests AS g
        LEFT JOIN guest_roles AS gr ON g.guest_id = gr.guest_id
        LEFT JOIN roles AS r ON gr.role_id = r.role_id
        WHERE r.role_name = 'resident' AND g.status = 'active'
        ORDER BY id DESC
    """
    cur.execute(query)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_active_reviewers():
    conn = get_connection()
    cur = conn.cursor()
    query = """
        SELECT 
            g.guest_id as id,
            g.name
        FROM guests AS g
        LEFT JOIN guest_roles AS gr ON g.guest_id = gr.guest_id
        LEFT JOIN roles AS r ON gr.role_id = r.role_id
        WHERE r.role_name = 'owner' AND g.status = 'active'
        ORDER BY id DESC
    """
    cur.execute(query)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows