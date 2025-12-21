from abc import ABC, abstractmethod
import os,json, cv2, random, threading, time,glob
import shutil
from datetime import datetime, timedelta,timezone

from matplotlib.style import context
from utilities.environment_variables import load_environment
from pathlib import Path
import face_recognition
#from master_faces_db import process_all_json_files
import numpy as np

import sqlite3
from utilities.environment_variables import load_environment
import logging
from json import JSONDecodeError
import face_recognition_worker

# Set up a simple logger (if not already configured in your app)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


load_environment("./../data/.env.yolocam")
from utilities.crypto_manager import crypto


class PrecessingStrategy(ABC):
    @abstractmethod
    def execute(self, array):
        pass

class PrecessingContext:
    def __init__(self, base_path: str, code: str):
        self.base_path = base_path          # only folder path
        self.code = code                      # file code (guest_id or any ID)

        # Create full paths
        self.json_filepath = os.path.join(base_path, f"{code}.json")
        self.wbem_filepath = os.path.join(base_path, f"{code}.webm")
        # ----------- LOAD JSON FILE -----------
        if not os.path.exists(self.json_filepath):
            raise FileNotFoundError(f"JSON file not found: {self.json_filepath}")

        with open(self.json_filepath, "r") as file:
            self.data = json.load(file)

        self.strategy = None
        print(f"Loaded: {self.json_filepath}")
        print(f"WBEM file path: {self.wbem_filepath}")


    def process(self):
        if self.strategy is None:
            raise Exception("Strategy not set")
        self.strategy.execute(self)

    def set_precessing_strategy(self, strategy):
        self.strategy = strategy

    def save(self):
        """Save updated JSON to its path"""
        with open(self.json_filepath, "w") as file:
            json.dump(self.data, file, indent=4)




class ExtractImageFromVideoStrategy(PrecessingStrategy):
    def execute(self, context):
        print("Processing using ExtractImageFromVideoStrategy")

        guest_name = context.data["guest_name"]
        print(f"Guest Name: {guest_name}")
        print(f"Email: {context.data['email']}")

        video_path = context.wbem_filepath
        if not os.path.exists(video_path):
            print(f"[WARN] Missing video file: {video_path}")
            return

        # Output folder
        output_folder = os.path.join(context.base_path, context.code)
        os.makedirs(output_folder, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        if total_frames <= 0 or fps <= 0:
            print(f"[WARN] Cannot read frames or FPS in {video_path}")
            cap.release()
            return

        # Pick random frames
        frame_numbers = random.sample(range(total_frames), min(300, total_frames))
        print(f"Selected Frames: {frame_numbers}")


        # 1. Load all existing JPG files in the output folder
        existing_files = sorted(glob.glob(os.path.join(output_folder, "*.jpg")))
        file_paths = existing_files.copy()     # start list with already existing files

        # 2. Set count = number of existing .jpg files + 1
        count = len(existing_files) + 1
        
        # file_paths = []
        # count = 1

        for frame_no in frame_numbers:
            if count > 3:  # limit to 3 images
                break

            # Convert frame number → timestamp in milliseconds
            timestamp_ms = (frame_no / fps) * 1000.0
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)

            ret, frame = cap.read()
            if not ret or frame is None:
                print(f"❌ Frame missing at {frame_no}")
                continue

            # Save image
            file_path = os.path.join(
                output_folder, f"{context.code}_{guest_name}_{count}.jpg"
            )
            cv2.imwrite(file_path, frame)
            file_paths.append(file_path)

            print(f"[SAVED] {file_path}")
            count += 1

        cap.release()
        # Save only if exactly 3 images were generated
        if len(file_paths) == 3:
            context.data["generated_images"] = file_paths
            context.save()
            print("[DONE] Extracted and saved EXACTLY 3 images.")
        else:
            print(f"[SKIPPED] Only {len(file_paths)} images generated — not saving.")


    # OLD function removed because it caused frame-loss problems

class ExtractFacesfromImage(PrecessingStrategy):

    def execute(self, context):
        print("Processing using ExtractFacesfromImage")

        generated_files = context.data.get("generated_images", [])

        if not generated_files:
            print("[WARN] No generated images found in JSON")
            return

        # Prepare output folder for cropped faces
        faces_folder = os.path.join(context.base_path, context.code, "faces")
        os.makedirs(faces_folder, exist_ok=True)

        encodings = []
        cropped_faces_files = []
        saved_faces = 0

        for img_path in generated_files:

            if not os.path.exists(img_path):
                print(f"[WARN] Missing image file: {img_path}")
                continue

            # Load image
            image = face_recognition.load_image_file(img_path)

            # Detect face locations
            face_locations = face_recognition.face_locations(image)

            if len(face_locations) == 0:
                print(f"[WARN] No face found in {img_path}")
                continue

            # Compute encodings
            face_encs = face_recognition.face_encodings(image, face_locations)

            for (top, right, bottom, left), enc in zip(face_locations, face_encs):

                # Add encoding to array
                encodings.append(enc.tolist())

                # Extract cropped face
                face_crop = image[top:bottom, left:right]

                # Save cropped image
                crop_path = os.path.join(
                    faces_folder,
                    f"{context.code}_face_{saved_faces+1}.jpg"
                )

                cv2.imwrite(crop_path, cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR))

                cropped_faces_files.append(crop_path)
                saved_faces += 1

                print(f"[SAVED] Cropped face → {crop_path}")

        # Save to JSON
        context.data["face_encodings"] = encodings
        context.data["cropped_faces"] = cropped_faces_files

        context.save()

        print(f"[DONE] Extracted {saved_faces} faces and saved encodings.")


class RegisterUserInDataBase(PrecessingStrategy):

    # ------------------------------------------------------------
    # Helper function OUTSIDE of execute()  (Correct place)
    # ------------------------------------------------------------
    def _insert_guest(self, cursor, guest_id, name, guest_type, comments, email, phone_number):
        
        if (guest_type.lower() == "resident") and (email == "N/A" or email.strip() == ""):
            raise ValueError("Email is required for Resident guest type.")


        if (guest_type.lower() == "employee") or (guest_type.lower() == "owner"):
                email =guest_id + "@gmail.com"


        
        
        # 1️⃣ Check if email exists
        cursor.execute("SELECT guest_id FROM guests WHERE email = ?", (email,))
        existing = cursor.fetchone()

        if existing:
            return existing[0]
        
        # 2️⃣ Insert into guests table
        cursor.execute("""
            INSERT INTO guests (guest_id, name, comments, email, phone_number,status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (guest_id, name, comments, email, phone_number,'_blank'))
        print(f"[Info] New Guest inserted.{guest_id}")
        # 3️⃣ Insert authentication record
        password_hash = crypto.encrypt("Pass@123")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT OR REPLACE INTO guest_auth 
            (guest_id, password_hash, is_active, created_at, updated_at)
            VALUES (?, ?, 1, ?, ?)
        """, (guest_id, password_hash, now, now))
        print(f"[Info] Guest auth record created.{guest_id}")
        # 4️⃣ Assign role
        role_id = 1 if guest_type.lower() == "resident" else \
                2 if guest_type.lower() == "employee" else 3

        cursor.execute("""
            INSERT OR IGNORE INTO guest_roles (guest_id, role_id, assigned_at)
            VALUES (?, ?, ?)
        """, (guest_id, role_id, datetime.now().strftime("%Y-%m-%d")))

        print(f"[Info] Assigned role {role_id} to guest {guest_id}")

        return guest_id


    # ------------------------------------------------------------
    # MAIN EXECUTE() METHOD
    # ------------------------------------------------------------
    def execute(self, context):
        print("[START] Register user in DB...")

        data = context.data

        # Validation
        if not data.get("confirmed"):
            print("[SKIP] Guest not confirmed.")
            return

        encodings = data.get("face_encodings", [])
        if not encodings or len(encodings) < 2:
            print("[SKIP] Need at least 2 face encodings.")
            return

        valid_encodings = [e for e in encodings if isinstance(e, list) and len(e) > 0]
        if len(valid_encodings) < 2:
            print("[SKIP] Not enough valid encodings.")
            return

        # DB Path
        DB_PATH = os.getenv("DB_PATH") or "./../data/WhiteHouse.db"
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            # Step 3: Insert Guest
            new_guest_id = datetime.now().strftime("%Y%m%d%H%M%S")

            guest_id = self._insert_guest(
                cursor,
                new_guest_id,
                data.get("guest_name") or "Unknown",
                data.get("guest_type") or "Unknown",
                data.get("comment") or "N/A",
                data.get("email") or "N/A",
                data.get("phone") or "N/A"
            )

            # Step 4: Insert Encodings
            for enc in valid_encodings:
                enc_json = json.dumps(enc)
                cursor.execute("""
                    INSERT INTO guest_faces (guest_id, encoding)
                    VALUES (?, ?)
                """, (guest_id, enc_json))

            conn.commit()

            # Step 5: Reload memory
            face_recognition_worker.load_known_faces()

            print(f"[SUCCESS] Registered guest: {guest_id}")
            print(f"[SUCCESS] Inserted {len(valid_encodings)} encodings.")

            # Step 6: Delete JSON file
            if os.path.exists(context.json_filepath):
                os.remove(context.json_filepath)

                output_folder = os.path.join(context.base_path, context.code)
                shutil.rmtree(output_folder)

                print(f"[CLEANUP] Deleted JSON → {context.json_filepath}")

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Failed to register guest: {e}")

        finally:
            conn.close()

        print("[DONE] Register user in DB.")
