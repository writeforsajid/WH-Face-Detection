import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from utilities.environment_variables import load_environment
import logging
from json import JSONDecodeError
import face_recognition_worker

# Set up a simple logger (if not already configured in your app)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


load_environment("./../data/.env.yolocam")
# --- CONFIG ---
VIDEOS_PATH=os.getenv("VIDEOS_PATH")
if VIDEOS_PATH is None: VIDEOS_PATH = "./../data/videos"

DB_PATH=os.getenv("DB_PATH")
if DB_PATH is None: DB_PATH = "./../data"





JSON_DIR =VIDEOS_PATH

# -----------------------
# 1️⃣ Database Connection
# -----------------------
def get_db_connection():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    return conn, cursor

# -----------------------
# 2️⃣ Generate Guest ID
# -----------------------
def generate_guest_id():
    return datetime.now().strftime("%Y%m%d%H%M%S")

# -----------------------
# 3️⃣ Insert guest into guests table
# -----------------------
def insert_guest(cursor, guest_id, name, guest_type, bed_no):
    cursor.execute("""
        INSERT INTO guests (guest_id, name, guest_type, bed_no, status)
        VALUES (?, ?, ?, ?, ?)
    """, (guest_id, name, guest_type, bed_no, 'inactive'))

# -----------------------
# 4️⃣ Insert face encodings
# -----------------------
def insert_face_encodings(cursor, guest_id, encodings):
    for enc in encodings:
        enc_json = json.dumps(enc)
        cursor.execute("""
            INSERT INTO guest_faces (guest_id, encoding)
            VALUES (?, ?)
        """, (guest_id, enc_json))


def load_json_file(json_file_path):
    with open(json_file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# -----------------------
# 5️⃣ Process single JSON file
# -----------------------
def process_json_file(cursor, json_file_path):
    """
    Processes a single guest JSON file:
    - Validates content
    - Inserts guest and encodings into DB
    - Deletes file after successful processing

    Returns:
        True  -> successfully processed
        False -> skipped or invalid file
    """
    # -----------------------
    # Step 1: Load JSON safely
    # -----------------------
    try:
        data = load_json_file(json_file_path)
    except FileNotFoundError:
        logging.error(f"❌ File not found: {json_file_path}")
        return False
    except JSONDecodeError as e:
        logging.error(f"❌ Invalid JSON format in {json_file_path}: {e}")
        return False
    except Exception as e:
        logging.exception(f"❌ Unexpected error reading {json_file_path}: {e}")
        return False

    # -----------------------
    # Step 2: Validate content
    # -----------------------
    if not isinstance(data, dict):
        logging.warning(f"⚠️ Invalid data format (expected dict) in {json_file_path}")
        return False

    if not data.get("confirmed"):
        logging.info(f"⏩ Skipping unconfirmed guest in {json_file_path}")
        return False

    encodings = data.get("face_encodings", [])
    if not isinstance(encodings, list):
        logging.warning(f"⚠️ face_encodings must be a list in {json_file_path}")
        return False

    # Filter out empty encodings (invalid entries)
    valid_encodings = [e for e in encodings if isinstance(e, list) and len(e) > 0]
    if len(valid_encodings) < 2:
        logging.info(f"⏩ Skipping guest (not enough valid encodings) in {json_file_path}")
        return False

    # -----------------------
    # Step 3: Generate and insert data
    # -----------------------
    try:
        guest_id = generate_guest_id()

        insert_guest(
            cursor,
            guest_id,
            data.get("name") or "Unknown",
            data.get("guest_type") or "Unknown",
            data.get("bed_no") or "N/A"
        )

        insert_face_encodings(cursor, guest_id, valid_encodings)
        face_recognition_worker.load_known_faces()
        
    except Exception as e:
        logging.exception(f"❌ Database insert failed for {json_file_path}: {e}")
        return False

    # -----------------------
    # Step 4: Delete file safely
    # -----------------------
    try:
        os.remove(json_file_path)
        logging.info(f"✅ Processed and deleted file: {json_file_path}")
        return True
    except FileNotFoundError:
        logging.warning(f"⚠️ File already deleted: {json_file_path}")
        return True  # not a critical failure
    except PermissionError:
        logging.error(f"❌ Permission denied while deleting {json_file_path}")
        return False
    except Exception as e:
        logging.exception(f"❌ Unexpected error deleting {json_file_path}: {e}")
        return False
# -----------------------
# 6️⃣ Process all JSON files in directory
# -----------------------
def process_all_json_files():
    conn, cursor = get_db_connection()
    try:
        
        for filename in os.listdir(JSON_DIR):
            if filename.endswith(".json"):
                file_path = os.path.join(JSON_DIR, filename)
                processed = process_json_file(cursor, file_path)
                if processed:
                    print(f"Processed and removed: {filename}")
        conn.commit()
    except Exception as e:
        print("Error:", e)
        conn.rollback()
    finally:
        conn.close()





















































def sync_json_to_db():
    """Read all .json files in VIDEOS_PATH and insert valid encodings into DB."""
    conn, cur = get_db_connection()
    inserted_total = 0

    json_files = [f for f in os.listdir(VIDEOS_PATH) if f.endswith(".json")]
    print(f"[INFO] Found {len(json_files)} JSON files to check.")

    for jf in json_files:
        filepath = VIDEOS_PATH / jf
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            guest_id = data.get("guest_id")
            enc_list = data.get("face_encodings", [])

            # --- Validation ---
            if not guest_id:
                print(f"[SKIP] Missing guest_id in {jf}")
                continue

            if not enc_list or len(enc_list) < 3:
                print(f"[SKIP] Less than 3 encodings for guest_id={guest_id}")
                continue

            # Check if encodings already exist for this guest_id
            cur.execute("SELECT COUNT(*) FROM guest_faces WHERE guest_id=?", (guest_id,))
            existing_count = cur.fetchone()[0]

            if existing_count >= 3:
                print(f"[INFO] Guest {guest_id} already has {existing_count} encodings. Skipping.")
                continue

            # --- Insert encodings ---
            added = 0
            for enc in enc_list:
                enc_json = json.dumps(enc)
                cur.execute(
                    "INSERT INTO guest_faces (guest_id, encoding) VALUES (?, ?)",
                    (guest_id, enc_json)
                )
                added += 1

            conn.commit()
            inserted_total += added
            print(f"[SUCCESS] Inserted {added} encodings for guest_id={guest_id}")

        except Exception as e:
            print(f"[ERROR] {jf}: {e}")

    conn.close()
    print(f"\n✅ Sync complete. Total new encodings inserted: {inserted_total}")
