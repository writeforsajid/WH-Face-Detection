import os
from datetime import datetime
import random,shutil
from utilities.environment_variables import load_environment
import uuid
import json
from typing import List, Dict
#import ffmpeg

#VIDEOS_PATH = "./data/videos"
load_environment("./../data/.env.webapp")
VIDEOS_PATH=os.getenv("VIDEOS_PATH","./../data/Videos")
STATIC_TEMP_PATH=os.getenv("STATIC_TEMP_PATH","./static/temp")
#VIDEOS_PATH=os.getenv("VIDEOS_PATH")
os.makedirs(VIDEOS_PATH, exist_ok=True)
os.makedirs(STATIC_TEMP_PATH, exist_ok=True)






async def save_uploaded_video(file, guest_name=None, guest_type=None, comment=None, email=None, phone=None):
    contents = await file.read()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    guest_id = generate_guid()
    filename = f"{guest_id}.webm"
    filepath = os.path.join(VIDEOS_PATH, filename)

    # --- Save Video File ---
    with open(filepath, "wb") as f:
        f.write(contents)

    file_size = os.path.getsize(filepath)

    # --- Save guest data in database ---
    #save_guest_data(guest_id, guest_name, guest_type, comment, email, phone)

    # --- Create JSON File with guest metadata ---
    json_path = os.path.join(VIDEOS_PATH, f"{guest_id}.json")

    face_encodings=[
        "",
        "",
        ""
    ]
    guest_data = {
        "guest_id": guest_id,
        "guest_name": guest_name,
        "guest_type": guest_type,
        "comment": comment,
        "email": email,
        "phone": phone,
        "confirmed": False,
        "uploaded_at": timestamp,
        "face_encodings": face_encodings
    }

    with open(json_path, "w") as json_file:
        json.dump(guest_data, json_file, indent=4)



    # --- Replace preview.webm ---
    dst = os.path.join(STATIC_TEMP_PATH, "preview.webm")
    try:
        if os.path.exists(dst):
            os.remove(dst)
    except Exception as e:
        print("Error deleting old preview:", e)

    shutil.copy2(filepath, dst)

    return {
        "status": "success",
        "guest_id": guest_id,
        "filename": filename,

        "path": filepath,
        "size_kb": round(file_size / 1024, 2),
        "message": "Video uploaded and zipped successfully"
    }

# # Directory where JSON files will be stored


import os, shutil, json, zipfile
from datetime import datetime

# async def save_uploaded_video(file, guest_name=None, guest_type=None, comment=None, email=None, phone=None):
#     contents = await file.read()
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

#     guest_id = generate_guid()
#     filename = f"{guest_id}.webm"
#     filepath = os.path.join(VIDEOS_PATH, filename)

#     # --- Save Video File ---
#     with open(filepath, "wb") as f:
#         f.write(contents)

#     file_size = os.path.getsize(filepath)

#     # --- Save guest data in database ---


#     face_encodings=[
#         "",
#         "",
#         ""
#     ]
#     guest_data = {
#         "guest_id": guest_id,
#         "name": guest_name,
#         "comment": comment,
#         "guest_type": guest_type,
#         "email": email,
#         "phone": phone,
#         "confirmed": False,
#         "face_encodings": face_encodings
#     }

#     filepath = os.path.join(VIDEOS_PATH, f"{guest_id}.json")

#     with open(filepath, "w", encoding="utf-8") as f:
#         json.dump(guest_data, f, indent=2, ensure_ascii=False)
# #    save_guest_data(guest_id, guest_name, guest_type, comment, email, phone)
#     # --- Create JSON File with guest metadata ---
#     json_path = os.path.join(VIDEOS_PATH, f"{guest_id}.json")
#     guest_data = {
#         "guest_id": guest_id,
#         "guest_name": guest_name,
#         "guest_type": guest_type,
#         "comment": comment,
#         "email": email,
#         "phone": phone,
#         "uploaded_at": timestamp
#     }

#     with open(json_path, "w") as json_file:
#         json.dump(guest_data, json_file, indent=4)

#     # --- Create ZIP containing video + JSON ---
#     zip_filename = f"{guest_id}.zip"
#     zip_path = os.path.join(VIDEOS_PATH, zip_filename)

#     with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
#         zipf.write(filepath, arcname=filename)
#         zipf.write(json_path, arcname=f"{guest_id}.json")

#     # --- Replace preview.webm ---
#     dst = os.path.join(STATIC_TEMP_PATH, "preview.webm")
#     try:
#         if os.path.exists(dst):
#             os.remove(dst)
#     except Exception as e:
#         print("Error deleting old preview:", e)

#     shutil.copy2(filepath, dst)

#     return {
#         "status": "success",
#         "guest_id": guest_id,
#         "filename": filename,
#         "zip_file": zip_filename,
#         "zip_path": zip_path,
#         "path": filepath,
#         "size_kb": round(file_size / 1024, 2),
#         "message": "Video uploaded and zipped successfully"
#     }



def generate_guid() -> str:
    """Generate a unique GUID string."""
    return str(uuid.uuid4())

def save_guest_data(guest_id: str, name: str, guest_type: str, comment: str,email: str, phone: str ) -> str:
    """
    Save guest data into a unique JSON file.
    Returns the JSON file path.
    """

    face_encodings=[
        "",
        "",
        ""
    ]
    guest_data = {
        "guest_id": guest_id,
        "name": name,
        "comment": comment,
        "guest_type": guest_type,
        "email": email,
        "phone": phone,
        "confirmed": False,
        "face_encodings": face_encodings
    }

    filepath = os.path.join(VIDEOS_PATH, f"{guest_id}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(guest_data, f, indent=2, ensure_ascii=False)

    return filepath


def confirm_guest(guest_id: str) -> bool:
    """
    Find the guest JSON file in VIDEOS_PATH and set 'confirmed' = True.
    Returns True if updated successfully, False if not found or failed.
    """
    try:

        filepath = os.path.join(VIDEOS_PATH, f"{guest_id}.json")
        json_path = os.path.join(VIDEOS_PATH, f"{guest_id}.json")
        video_path = os.path.join(VIDEOS_PATH, f"{guest_id}.webm")
        breakpoint();
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

    except Exception as e:
        print(f"⚠️ Error updating guest {guest_id}: {e}")
        return False
