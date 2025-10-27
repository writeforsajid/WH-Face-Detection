import threading
import face_recognition
import sqlite3
import numpy as np
from datetime import datetime, timedelta
import os
import cv2  # ✅ Needed for saving cropped faces
from dotenv import load_dotenv
from typing import Optional

from utilities.environment_variables import load_environment
from utilities.file_manager import FileManager
# --------------------- CONFIG ---------------------

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "WhiteHouse.db")
DB_LOCK = threading.Lock()
cooldown = timedelta(seconds=30)



#load_dotenv(dotenv_path="./data/.env.yolocam")


load_environment("./../data/.env.yolocam")
OT=os.getenv("OT")
if OT is None: OT = "./../data/detected_frames"
CAMERA_ID = os.getenv("CAMERA_ID")
if CAMERA_ID is None: CAMERA_ID = "LIFT"
OT = os.path.join(OT, CAMERA_ID)
os.makedirs(OT, exist_ok=True)

# --------------------- Globals ---------------------
known_faces_encodings = []
known_faces_names = []
last_seen = {}  # photo_id -> datetime of last attendance

# --------------------- DB CONNECTION ---------------------
DB = sqlite3.connect(DB_PATH, check_same_thread=False)


_tolerance = os.getenv("TOLERANCE")
if _tolerance is None: _tolerance=float(0.50)
else: _tolerance=float(_tolerance)  



attendance_log = {}
known_faces_encodings = []
known_faces_names = []
def load_known_faces():
    """Load known face encodings from the DB."""
    global known_faces_encodings, known_faces_names
    known_faces_encodings = []
    known_faces_names = []

    try:
        cur = DB.cursor()
        cur.execute("SELECT gf.guest_id, gf.encoding FROM guest_faces AS gf JOIN guests AS g ON gf.guest_id = g.guest_id WHERE (g.status = 'active' or g.status = 'leave')")
        rows = cur.fetchall()
    except Exception:
        rows = []

    for guest_id, encoding_str in rows:
        encoding = np.array(eval(encoding_str), dtype="float32")
        known_faces_encodings.append(encoding)
        known_faces_names.append(guest_id)

    
    print(f"[INFO] Loaded {len(known_faces_names)} known people")
    

def mark_attendance(photo_id, ts=datetime.now(), device_id="OUT", method="Face"):
    device_id=os.getenv("CAMERA_ID")
    # Cooldown check
    if photo_id in last_seen and ts - last_seen[photo_id] < cooldown:
        print(f"[ATTENDANCE] Skipping {photo_id} (within cooldown)")
        return False

    with DB_LOCK:
        cur = DB.cursor()
        cur.execute(
            "INSERT INTO attendance (guest_id, device_id, method, timestamp) VALUES (?,?,?,?)",
            (photo_id, device_id, method, ts.isoformat())
        )
        DB.commit()

    last_seen[photo_id] = ts
    print(f"[ATTENDANCE] Marked {photo_id} at {ts.isoformat()}")
    return True


def get_person_files(photo_id):
    """Return all files for a given person ID."""
    pattern = f"{photo_id}_"
    files = []
    if not os.path.exists(OT):
        return files

    for f in os.listdir(OT):
        if f.startswith(pattern) and f.endswith(".jpg"):
            full_path = os.path.join(OT, f)
            # Extract file number and person count from filename
            parts = f.replace(".jpg", "").split("_")
            
            file_num = int(parts[1])
            person_count = int(parts[2])
            date_time = datetime.fromtimestamp(os.path.getmtime(full_path))
            files.append({
                "path": full_path,
                "file_num": file_num,
                "person_count": person_count,
                "datetime": date_time
            })
    files.sort(key=lambda x: x["person_count"], reverse=True)
    return files





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
def run_face_recognition_Old(photo_id):
    """Process saved frames -> detect faces -> save cropped -> encode + attendance."""
    print(f"[THREAD] Starting recognition for Person {photo_id}...")

    
    files = get_person_files(photo_id)
    #--------------------!IMP---------selected_files = select_top_images(files) #!IMPORTANT
    selected_files = get_best_images(files) #!IMPORTANT


    if not selected_files:
        print(f"[THREAD] No files found for Person {photo_id}")
        return

    # Create subfolder for cropped faces
    person_folder = os.path.join(OT, str(photo_id))
    os.makedirs(person_folder, exist_ok=True)

    if 'known_faces_encodings' not in globals() or not known_faces_encodings:
        load_known_faces()
    for f in selected_files:
        image = face_recognition.load_image_file(f["path"])
        face_locations = face_recognition.face_locations(image)
        encodings = face_recognition.face_encodings(image, face_locations)
        primary_name = os.path.splitext(os.path.basename(f["path"]))[0]
        imgname = os.path.join(person_folder, f"{primary_name}.jpg")
        cv2.imwrite(imgname, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        print(f"[INFO] Image saved: {imgname}")

        for i, (loc, enc) in enumerate(zip(face_locations, encodings)):
            top, right, bottom, left = loc
            face_img = image[top:bottom, left:right]

            # Save cropped face to subfolder
            crop_name = os.path.join(person_folder, f"{primary_name}_face_{i+1}.jpg")
            cv2.imwrite(crop_name, cv2.cvtColor(face_img, cv2.COLOR_RGB2BGR))
            print(f"[INFO] Cropped face saved: {crop_name}")
            # Compare current encoding with known faces
            matches = face_recognition.compare_faces(known_faces_encodings, enc, tolerance=_tolerance)
            face_distances = face_recognition.face_distance(known_faces_encodings, enc)
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


    is_docker = os.path.exists("/.dockerenv")
    if is_docker:
        FileManager.delete_files_from_list(files)
        FileManager.delete_folder_and_all_contents(person_folder)
        FileManager.delete_old_files(os.path.dirname(person_folder),5)




# ---------------------------------------------------
# FACE CROPPING + RECOGNITION
# ---------------------------------------------------
def run_face_recognition(photo_id):
    """Process saved frames -> detect faces -> save cropped -> encode + attendance."""
    print(f"[THREAD] Starting recognition for Person {photo_id}...")
    
    if photo_id is None:
        print(f"[THREAD] No valid photo_id provided.")
        return
    if "_" in photo_id:
        photo_id = photo_id.split("_")[0]
    # Otherwise, return the original string
    
    
    selected_files = get_person_files(photo_id)
    #--------------------!IMP---------selected_files = select_top_images(files) #!IMPORTANT
    #selected_files = get_best_images(files) #!IMPORTANT


    if not selected_files:
        print(f"[THREAD] No files found for Person {photo_id}")
        return

    # Create subfolder for cropped faces
    person_folder = os.path.join(OT, str(photo_id))
    os.makedirs(person_folder, exist_ok=True)

    if 'known_faces_encodings' not in globals() or not known_faces_encodings:
        load_known_faces()
    for f in selected_files:
        image = face_recognition.load_image_file(f["path"])
        face_locations = face_recognition.face_locations(image)
        encodings = face_recognition.face_encodings(image, face_locations)
        primary_name = os.path.splitext(os.path.basename(f["path"]))[0]
        imgname = os.path.join(person_folder, f"{primary_name}.jpg")
        cv2.imwrite(imgname, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        print(f"[INFO] Image saved: {imgname}")

        for i, (loc, enc) in enumerate(zip(face_locations, encodings)):
            top, right, bottom, left = loc
            face_img = image[top:bottom, left:right]

            # Save cropped face to subfolder
            crop_name = os.path.join(person_folder, f"{primary_name}_face_{i+1}.jpg")
            cv2.imwrite(crop_name, cv2.cvtColor(face_img, cv2.COLOR_RGB2BGR))
            print(f"[INFO] Cropped face saved: {crop_name}")
            # Compare current encoding with known faces
            matches = face_recognition.compare_faces(known_faces_encodings, enc, tolerance=_tolerance)
            face_distances = face_recognition.face_distance(known_faces_encodings, enc)
            best_match_index = np.argmin(face_distances) if len(face_distances) > 0 else None

            if True in matches and best_match_index is not None:
                person_name = known_faces_names[best_match_index]
                print(f"[INFO] Recognized known person: {person_name}")
            else:
                person_name = "unknown"
                print(f"[INFO] Unknown person detected in {crop_name}")

            # ✅ Always mark attendance
            mark_attendance(person_name,f["datetime"])

    print(f"[THREAD] Recognition complete for {photo_id}.")

    FileManager.delete_files_from_list(selected_files)
    is_docker = os.path.exists("/.dockerenv")
    if is_docker:
        FileManager.delete_folder_and_all_contents(person_folder)
        #FileManager.delete_old_files(os.path.dirname(person_folder),5)




def get_unprocessed_file_id(folder_path: str) -> Optional[str]:
    """
    Scans the given folder for .jpg files and extracts the first photo_id found.
    photo_id is defined as the part before the first underscore in the filename.
    Example filename: 251023222658069_3_01_2.jpg  -> photo_id = '251023222658069'
    
    Returns:
        - photo_id (str): if found and no folder with that name exists
        - None: if no valid .jpg files found
    """
    # Ensure folder exists
    if not os.path.isdir(folder_path):
        raise ValueError(f"Folder not found: {folder_path}")

    # List all .jpg files
    jpg_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".jpg")]

    if not jpg_files:
        return None  # No JPG files found

    # Extract first photo_id
    for filename in jpg_files:
        parts = filename.split("_")
        if len(parts) > 1:
            photo_id = parts[0]
            # Ensure no folder exists with this name
            possible_folder = os.path.join(folder_path, photo_id)
            if not os.path.exists(possible_folder):
                return photo_id

    return None  # No unprocessed photo_id found



def delete_person_files(photo_id):
    """Delete all saved frames of a given person."""
    pattern = f"Person_{photo_id}_"
    if not os.path.exists(OT):
        return
    for f in os.listdir(OT):
        if f.startswith(pattern) and f.endswith(".jpg"):
            os.remove(os.path.join(OT, f))
    print(f"[INFO] Deleted all frames for Person {photo_id}")


def start_face_recognition_thread(photo_id):
    """Start face recognition in a separate thread."""
    thread = threading.Thread(target=run_face_recognition, args=(photo_id,), daemon=True)
    thread.start()
    return thread




# def select_top_images(files):
#     """Select top 3 images: priority on person_count, latest, random"""
#     if not files:
#         return []

#     files.sort(key=lambda f: (f["person_count"], f["time"]), reverse=True)
#     top_files = files[:5]
#     random.shuffle(top_files)
#     return top_files[:3]


# def update_attendance(photo_id):
#     for person_file in selected_files:
#         # Extract photo_id from filename
#         # e.g., Person_21_02_1.jpg -> 21
#         fname = os.path.basename(person_file["path"])
#         photo_id = int(fname.split("_")[1])
#         mark_attendance(photo_id)



# def run_face_recognition(photo_id): 
#     """Threaded face recognition for a person with DB attendance."""
#     print(f"[THREAD] Starting recognition for Person {photo_id}...")

#     files = get_person_files(photo_id)
#     selected_files = select_top_images(files)
#     if not selected_files:
#         print(f"[THREAD] No files found for Person {photo_id}")
#         return

#     for f in selected_files:
#         image = face_recognition.load_image_file(f["path"])
#         encodings = face_recognition.face_encodings(image)
#         for enc in encodings:
#             # Compare current encoding with known faces
#             matches = face_recognition.compare_faces(known_faces_encodings, enc, tolerance=0.8)
#             face_distances = face_recognition.face_distance(known_faces_encodings, enc)
#             if len(face_distances) > 0:
#                 best_match_index = np.argmin(face_distances)
#                 print(f"[INFO] Face distances: {best_match_index}")
#             else:
#                 best_match_index = None

#             if True in matches and best_match_index is not None:
#                 # ✅ Known person found
#                 person_name = known_faces_names[best_match_index]
#                 print(f"[INFO] Recognized known person: {person_name}")
#             else:
#                 # 🚨 Unknown person
#                 person_name = "unknown"
#                 print(f"[INFO] Unknown person detected in {f['path']}")

#             # ✅ Mark attendance (always)
#             mark_attendance(person_name)

#     print(f"[THREAD] Recognition complete for {photo_id}.")
