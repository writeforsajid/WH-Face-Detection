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






async def save_uploaded_video(file, guest_name=None, guest_type=None,bed_no=None):
    """
    Save uploaded video in /data/videos and return metadata + thumbnails.
    """

    contents = await file.read()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = (guest_name or "guest").replace(" ", "_")
    guest_id = generate_guid()
    filename = f"{guest_id}.webm"
    filepath = os.path.join(VIDEOS_PATH, filename)

    # Save file
    with open(filepath, "wb") as f:
        f.write(contents)

    file_size = os.path.getsize(filepath)
    save_guest_data(guest_id,guest_name, guest_type,bed_no)
    dst = os.path.join(STATIC_TEMP_PATH, "preview.webm")
    shutil.copy2(filepath, dst)

    return {
        "status": "success",
        "guest_id":guest_id,
        "filename": filename,
        "path": filepath,
        "size_kb": round(file_size / 1024, 2),
        "message": "Video uploaded successfully"
    }

# Directory where JSON files will be stored



def generate_guid() -> str:
    """Generate a unique GUID string."""
    return str(uuid.uuid4())

def save_guest_data(guest_id: str, name: str, guest_type: str, bed_no: str ) -> str:
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
        "bed_no": bed_no,
        "guest_type": guest_type,
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
