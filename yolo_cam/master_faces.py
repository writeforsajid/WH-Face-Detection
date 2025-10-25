import os, json, cv2, random, threading, time
from datetime import datetime, timedelta
from utilities.environment_variables import load_environment
from pathlib import Path
import face_recognition
from master_faces_db import process_all_json_files


load_environment("./../data/.env.yolocam")
VIDEOS_PATH=os.getenv("VIDEOS_PATH")
if VIDEOS_PATH is None: VIDEOS_PATH = "./../data/videos"
PROCESS_INTERVAL_HOURS = 1   # production
DEV_MODE = True              # ✅ switch to True for testing

if DEV_MODE:
    PROCESS_INTERVAL_HOURS = 0.05  # ~3 minutes for testing

last_process_time = datetime.min
stop_requested = False


def process_confirmed_videos():
    """Scan VIDEOS_PATH and process up to 5 confirmed guest videos."""
    try:

        confirmed_files = get_confirmed_files()

        if not confirmed_files:
            print("[INFO] No confirmed guests pending for processing.")
            return

        confirmed_files = confirmed_files[:5]  # ✅ Safe slicing

        print(f"[INFO] Found {len(confirmed_files)} confirmed guests to process.")
        
        for jf, data in confirmed_files:
            guest_id = data["guest_id"]
            name = data["name"]
            video_path = os.path.join(VIDEOS_PATH, f"{guest_id}.webm")

            if not os.path.exists(video_path):
                print(f"[WARN] Missing video for {guest_id}: {video_path}")
                continue

            # Spawn worker thread per video

            process_single_video(video_path, data, jf)

            #thread = threading.Thread(target=process_single_video, args=(video_path, data, jf))
            #thread.daemon = True
            #thread.start()

        process_all_json_files()
    
    except Exception as e:
        print(f"[ERROR] process_confirmed_videos(): {e}")






VIDEOS_PATH = "./../data/videos"  # Make sure this exists



def process_single_video(video_path: str, guest_data: dict, json_filename: str):
    """
    Extract up to 3 face encodings from random frames in a video
    and save both cropped face images and encodings in the guest JSON file.
    """
    try:
        # Ensure output directory exists
        os.makedirs(VIDEOS_PATH, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            print(f"[WARN] No frames found in {video_path}")
            cap.release()
            return

        # Randomly sample up to 25 frames to improve chances, but only pick max 3 valid faces
        random_frames = sorted(random.sample(range(total_frames), min(25, total_frames)))
        encodings = []
        saved_faces = 0

        for frame_no in random_frames:
            if saved_faces >= 3:
                break

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            # Convert BGR → RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Step 1: detect faces
            face_locations = face_recognition.face_locations(rgb, model="hog")

            # Step 2: compute encodings
            face_encs = face_recognition.face_encodings(rgb, face_locations)

            # Step 3: crop and save each face
            for i, (loc, enc) in enumerate(zip(face_locations, face_encs)):
                if saved_faces >= 3:
                    break

                top, right, bottom, left = loc
                face_crop = frame[top:bottom, left:right]

                # Save cropped face image (for debugging/inspection)
                face_filename = os.path.join(
                    VIDEOS_PATH,
                    f"{guest_data.get('name','unknown').replace(' ', '_')}_face_{saved_faces+1}.jpg"
                )
                cv2.imwrite(face_filename, face_crop)

                # Store encoding
                encodings.append(enc.tolist())
                saved_faces += 1
                print(f"[INFO] Saved cropped face {saved_faces} for {guest_data.get('name','Unknown')} at frame {frame_no}")

        cap.release()

        # ✅ Save encodings to JSON if found
        if encodings:
            guest_data["face_encodings"] = encodings
            json_path = os.path.join(VIDEOS_PATH, json_filename)
            save_face_encodings_json(guest_data, encodings, json_path,3)
            print(f"[SUCCESS] Saved {len(encodings)} encodings + face crops for {guest_data.get('name','Unknown')} → {json_path}")
        else:
            print(f"[INFO] No faces found in {video_path}")

    except Exception as e:
        print(f"[ERROR] process_single_video({video_path}): {e}")




import json
import os

def save_face_encodings_json(guest_data: dict, encodings: list, json_path: str, max_limit: int = 3):
    """
    Merge new encodings into existing JSON file (if any),
    ensuring there are at most `max_limit` encodings total.
    """
    try:
        # ✅ If file exists, read existing encodings
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            existing_enc = existing_data.get("face_encodings", [])
        else:
            existing_data = {}
            existing_enc = []



        # ✅ Combine existing + new (avoid exceeding max limit)
        combined_enc = existing_enc + encodings

        # Remove empty, None, or short encodings
        combined_enc = [
            e for e in combined_enc 
            if isinstance(e, list) and len(e) > 10  # 128-length check relaxed
        ]

        # ✅ Limit to 3 max
        combined_enc = combined_enc[:max_limit]



        # ✅ Update guest data (preserve other fields)
        merged_data = {**existing_data, **guest_data}
        merged_data["face_encodings"] = combined_enc

        # ✅ Save final JSON
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)

        print(f"[SUCCESS] {len(combined_enc)} encodings saved to {json_path}")

    except Exception as e:
        print(f"[ERROR] save_face_encodings_json({json_path}): {e}")


def get_confirmed_files():
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

    return confirmed_files


# ✅ Background trigger every hour without blocking main loop
def thread_video_process():
    global last_process_time
    now = datetime.now()
    if now - last_process_time >= timedelta(hours=PROCESS_INTERVAL_HOURS):
        last_process_time = now
        print(f"\n[INFO] Starting background video processing @ {now}")
        threading.Thread(target=process_confirmed_videos, daemon=True).start()


#if __name__ == "__main__":


    #load_environment("./../data/.env.yolocam")
    #process_confirmed_videos()
    #process_all_json_files()