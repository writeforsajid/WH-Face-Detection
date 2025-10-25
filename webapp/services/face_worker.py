import threading
import os
# import cv2
# import face_recognition
import json
from pathlib import Path
from db.database import get_connection

VIDEO_DIR = "./data/videos"

def process_guest_video_async(guest_id: str, guest_name: str):
    """Start background thread to process guest video and extract encodings."""
    thread = threading.Thread(target=_process_guest_video, args=(guest_id, guest_name))
    thread.daemon = True
    thread.start()


def _process_guest_video(guest_id: str, guest_name: str):
    """Background worker: extract frames, encode faces, save images, and insert into DB."""
    try:
        guest_name_safe = guest_name.replace(" ", "_")

        # Find matching video
        video_files = [f for f in os.listdir(VIDEO_DIR) if f.startswith(guest_name_safe) and f.endswith(".webm")]
        if not video_files:
            print(f"[WARN] No video found for {guest_name}")
            return

        # Use latest uploaded video
        video_files.sort(key=lambda f: os.path.getmtime(os.path.join(VIDEO_DIR, f)), reverse=True)
        video_filename = video_files[0]
        video_path = os.path.join(VIDEO_DIR, video_filename)

        # Create output folder (same name as video file)
        output_folder = Path(VIDEO_DIR) / Path(video_filename).stem
        output_folder.mkdir(exist_ok=True)

        # Move video inside that folder if not already
        if os.path.dirname(video_path) != str(output_folder):
            os.rename(video_path, output_folder / video_filename)
            video_path = str(output_folder / video_filename)

        print(f"[INFO] Processing video for {guest_name}: {video_path}")

        # cap = cv2.VideoCapture(video_path)
        # frame_count = 0
        # encodings_saved = 0

        # conn = get_connection()
        # cur = conn.cursor()

        # while True:
        #     ret, frame = cap.read()
        #     if not ret:
        #         break

        #     frame_count += 1
        #     if frame_count % 15 != 0:  # every 10th frame
        #         continue

        #     rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        #     face_locations = face_recognition.face_locations(rgb_frame)
        #     encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        #     if len(encodings) == 0:
        #         continue

        #     # Save frame image
        #     frame_filename = output_folder / f"frame_{encodings_saved+1:02d}.jpg"
        #     cv2.imwrite(str(frame_filename), frame)

        #     # Save cropped face(s)
        #     for i, (top, right, bottom, left) in enumerate(face_locations):
        #         face_crop = frame[top:bottom, left:right]
        #         face_filename = output_folder / f"face_{encodings_saved+1:02d}.jpg"
        #         cv2.imwrite(str(face_filename), face_crop)
        #         break  # only first face per frame

        #     # Save encoding in DB
        #     encoding_json = json.dumps(encodings[0].tolist())
        #     cur.execute(
        #         "INSERT INTO guest_faces (guest_id, encoding) VALUES (?, ?)",
        #         (guest_id, encoding_json)
        #     )

        #     encodings_saved += 1
        #     if encodings_saved >= 3:
        #         break

        # conn.commit()
        # conn.close()
        # cap.release()
        # print(f"[SUCCESS] Saved {encodings_saved} encodings and images for guest {guest_name}")

    except Exception as e:
        print(f"[ERROR] Failed to process video for {guest_name}: {e}")
