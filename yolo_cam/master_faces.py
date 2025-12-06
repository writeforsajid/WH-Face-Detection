import os, json, cv2, random, threading, time,random
from datetime import datetime, timedelta,timezone
from utilities.environment_variables import load_environment
from pathlib import Path
import face_recognition
#from master_faces_db import process_all_json_files
from UserRegistrationVideo import PrecessingContext, ExtractImageFromVideoStrategy,ExtractFacesfromImage,RegisterUserInDataBase
import json
import os


load_environment("./../data/.env.yolocam")
VIDEOS_PATH=os.getenv("VIDEOS_PATH")
if VIDEOS_PATH is None: VIDEOS_PATH = "./../data/videos"
PROCESS_INTERVAL_HOURS = 1 * .50   # production


def is_docker():
    return os.path.exists("/.dockerenv")

if not is_docker:
    PROCESS_INTERVAL_HOURS = 0.05  # ~3,~15 minutes for testing

last_process_time = datetime.min
stop_requested = False


def process_confirmed_videos():
    """Scan VIDEOS_PATH and process up to 5 confirmed guest videos."""
    try:

        result = get_confirmed_file()

        if not result:
            print("[INFO] No confirmed guests pending for processing.")
            return

        file_name, data = result
        guest_id = data["guest_id"]
        ctx = PrecessingContext(
            base_path=VIDEOS_PATH, 
            code=guest_id
        )

        ctx.set_precessing_strategy(ExtractImageFromVideoStrategy())
        ctx.process()
        ctx.set_precessing_strategy(ExtractFacesfromImage())
        ctx.process()
        ctx.set_precessing_strategy(RegisterUserInDataBase())
        ctx.process()    
    except Exception as e:
        print(f"[ERROR] process_confirmed_videos(): {e}")










def get_confirmed_file():
    """
    Return list of confirmed guest JSON files (with empty or missing face_encodings).
    Each item = (filename, data_dict)
    """

    confirmed_files = []
    try:
        json_files = [f for f in os.listdir(VIDEOS_PATH) if f.endswith(".json")]

        for jf in json_files:
            filepath = os.path.join(VIDEOS_PATH, jf)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # ✅ Conditions:
            confirmed = data.get("confirmed") is True

            enc = data.get("face_encodings",[])

            #enc_blank = (not enc) or (isinstance(enc, list) and all(not bool(e) for e in enc)) or (isinstance(enc, list) and len(enc) <= 1)
            enc_blank = not (isinstance(enc, list) and len(enc) >= 2 and all(bool(e) for e in enc))
            

            if confirmed and enc_blank:
                
                confirmed_files.append((jf, data))

    except Exception as e:
        print(f"[ERROR] get_confirmed_files(): {e}")

    # If nothing found → return None
    if not confirmed_files:
        return None

    # Otherwise return first entry
    return random.choice(confirmed_files)

# ✅ Background trigger every hour without blocking main loop
def thread_video_process():
    global last_process_time
    now = datetime.now()
    if now - last_process_time >= timedelta(hours=PROCESS_INTERVAL_HOURS):
        last_process_time = now
        print(f"\n[INFO] Starting background video processing @ {now}")
        threading.Thread(target=process_confirmed_videos, daemon=True).start()


# if __name__ == "__main__":
#     load_environment("./../data/.env.yolocam")
#     process_confirmed_videos()