import time
import threading
import random
import face_recognition
import sqlite3
import numpy as np
from datetime import datetime, timedelta
import os
import cv2  # ✅ Needed for saving cropped faces


# --------------------- CONFIG ---------------------
FOLDER_PATH = "detected_frames"
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "WhiteHouse.db")
DB_LOCK = threading.Lock()
cooldown = timedelta(seconds=30)

# --------------------- Globals ---------------------
known_faces_encodings = []
known_faces_names = []
last_seen = {}  # guest_id -> datetime of last attendance

# --------------------- DB CONNECTION ---------------------
DB = sqlite3.connect(DB_PATH, check_same_thread=False)


# ---------------------------------------------------
# FACE RECOGNITION HELPERS
# ---------------------------------------------------
def load_known_faces():
    """Load known face encodings from the DB."""
    global known_faces_encodings, known_faces_names
    known_faces_encodings = []
    known_faces_names = []

    try:
        cur = DB.cursor()
        cur.execute("SELECT gf.guest_id, gf.encoding FROM guest_faces AS gf JOIN guests AS g ON gf.guest_id = g.guest_id WHERE g.status = 'active'")
        rows = cur.fetchall()
    except Exception:
        rows = []

    for guest_id, encoding_str in rows:
        encoding = np.array(eval(encoding_str), dtype="float32")
        known_faces_encodings.append(encoding)
        known_faces_names.append(guest_id)

    print(f"[INFO] Loaded {len(known_faces_names)} known people")


def mark_attendance(guest_id, device_id="OUT", method="Face"):
    """Insert attendance record in DB with cooldown."""
    ts = datetime.now()
    if guest_id in last_seen and ts - last_seen[guest_id] < cooldown:
        print(f"[ATTENDANCE] Skipping {guest_id} (within cooldown)")
        return False

    with DB_LOCK:
        cur = DB.cursor()
        cur.execute(
            "INSERT INTO attendance (guest_id, device_id, method, timestamp) VALUES (?,?,?,?)",
            (guest_id, device_id, method, ts.isoformat())
        )
        DB.commit()

    last_seen[guest_id] = ts
    print(f"[ATTENDANCE] Marked {guest_id} at {ts.isoformat()}")
    return True


def get_person_files(photo_id):
    """Return all files for a given person ID."""
    pattern = f"{photo_id}_"
    files = []
    if not os.path.exists(FOLDER_PATH):
        return files

    for f in os.listdir(FOLDER_PATH):
        if f.startswith(pattern) and f.endswith(".jpg"):
            full_path = os.path.join(FOLDER_PATH, f)
            parts = f.replace(".jpg", "").split("_")

            file_num = int(parts[1])
            person_count = int(parts[2])
            modified_time = os.path.getmtime(full_path)
            files.append({
                "path": full_path,
                "file_num": file_num,
                "person_count": person_count,
                "time": modified_time
            })

    return files


def select_top_images(files):
    """Select top 3 images: priority on person_count, latest, random."""
    if not files:
        return []

    files.sort(key=lambda f: (f["person_count"], f["time"]), reverse=True)
    top_files = files[:5]
    random.shuffle(top_files)
    return top_files[:3]


def get_best_images(files, top_n=3):
    """Return top N best (most stable) images from given file list."""
    if not files:
        return []

    def blur_score(path):
        image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return 0
        return cv2.Laplacian(image, cv2.CV_64F).var()

    # Calculate sharpness for each file
    for f in files:
        try:
            f["clarity"] = blur_score(f["path"])
        except Exception:
            f["clarity"] = 0

    # Sort by clarity (descending order)
    sorted_files = sorted(files, key=lambda x: x["clarity"], reverse=True)

    # Return top 3 (or top_n) same structure
    return sorted_files[:top_n]

# ---------------------------------------------------
# FACE CROPPING + RECOGNITION
# ---------------------------------------------------
def run_face_recognition(photo_id):
    """Process saved frames -> detect faces -> save cropped -> encode + attendance."""
    print(f"[THREAD] Starting recognition for Person {photo_id}...")

    files = get_person_files(photo_id)
    selected_files = get_best_images(files)
    if not selected_files:
        print(f"[THREAD] No files found for Person {photo_id}")
        return

    # Create subfolder for cropped faces
    person_folder = os.path.join(FOLDER_PATH, str(photo_id))
    os.makedirs(person_folder, exist_ok=True)

    for f in selected_files:
        image = face_recognition.load_image_file(f["path"])
        face_locations = face_recognition.face_locations(image)
        encodings = face_recognition.face_encodings(image, face_locations)

        for i, (loc, enc) in enumerate(zip(face_locations, encodings)):
            top, right, bottom, left = loc
            face_img = image[top:bottom, left:right]

            # Save cropped face to subfolder
            crop_name = os.path.join(person_folder, f"{photo_id}_face_{i+1}.jpg")
            cv2.imwrite(crop_name, cv2.cvtColor(face_img, cv2.COLOR_RGB2BGR))
            print(f"[INFO] Cropped face saved: {crop_name}")

            # Compare current encoding with known faces
            matches = face_recognition.compare_faces(known_faces_encodings, enc, tolerance=0.7)
            face_distances = face_recognition.face_distance(known_faces_encodings, enc)
            print(f"[INFO] Face distance {face_distances}")       
            best_match_index = np.argmin(face_distances) if len(face_distances) > 0 else None

            if True in matches and best_match_index is not None:
                person_name = known_faces_names[best_match_index]
                print(f"[INFO] Recognized known person: {person_name}")
            else:
                person_name = "unknown"
                print(f"[INFO] Unknown person detected in {crop_name}")

            # ✅ Always mark attendance
            mark_attendance(person_name)

    print(f"[THREAD] Recognition complete for {photo_id}.")


def delete_person_files(photo_id):
    """Delete all saved frames of a given person."""
    if not os.path.exists(FOLDER_PATH):
        return
    for f in os.listdir(FOLDER_PATH):
        if f.startswith(f"{photo_id}_") and f.endswith(".jpg"):
            os.remove(os.path.join(FOLDER_PATH, f))
    subfolder = os.path.join(FOLDER_PATH, str(photo_id))
    if os.path.exists(subfolder):
        for f in os.listdir(subfolder):
            os.remove(os.path.join(subfolder, f))
        os.rmdir(subfolder)
    print(f"[INFO] Deleted all frames for Person {photo_id}")


def start_face_recognition_thread(photo_id):
    """Run face recognition in a separate thread."""
    thread = threading.Thread(target=run_face_recognition, args=(photo_id,), daemon=True)
    thread.start()
    return thread
