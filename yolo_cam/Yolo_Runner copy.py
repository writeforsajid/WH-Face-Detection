from dotenv import load_dotenv, find_dotenv
from ultralytics import YOLO


import cv2, threading, queue, time, datetime, os
import numpy as np
import sys
from master_faces import maybe_trigger_hourly_process
from datetime import datetime, timedelta



# Add parent directory for utilities
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from face_recognition_worker import run_face_recognition
from utilities.crypto_manager import CryptoManager
from utilities.environment_variables import load_environment


OT=os.getenv("OT")
if OT is None: OT = "./../data/detected_frames"
CAMERA_ID = os.getenv("CAMERA_ID")
if CAMERA_ID is None: CAMERA_ID = "LIFT"
OT = os.path.join(OT, CAMERA_ID)
os.makedirs(OT, exist_ok=True)

# ------------------- Threaded YOLO Worker -------------------
class YOLOWorker:
    def __init__(self, model_path="yolov8n.pt", conf=0.5):
        self.model = YOLO(model_path)
        self.conf = conf
        self.q_in = queue.Queue(maxsize=5)
        self.q_out = queue.Queue(maxsize=5)
        self.stopped = False

    def start(self):
        t = threading.Thread(target=self._infer, daemon=True)
        t.start()
        return self

    def _infer(self):
        while not self.stopped:
            frame = self.q_in.get()
            if frame is None:
                break
            results = self.model(frame, conf=self.conf, verbose=False)
            self.q_out.put((frame, results))

    def infer_async(self, frame):
        if not self.q_in.full():
            self.q_in.put(frame)

    def get_results(self):
        if not self.q_out.empty():
            return self.q_out.get()
        return None, None

    def stop(self):
        self.stopped = True
        self.q_in.put(None)


# ------------------- Save Frame -------------------
def save_frame(frame, photo_id, frame_num, total_humans,
               frame_top, frame_bottom, frame_left, frame_right):
    """Crop and save detected frame image."""
    os.makedirs(OT, exist_ok=True)
    
    # Crop the frame using region of interest (ROI)
    cropped = frame[frame_top:frame_bottom, frame_left:frame_right]
    
    # Construct filename
    filename = f"{OT}/{photo_id}_{frame_num:02d}_{total_humans}.jpg"
    
    # Save cropped image
    cv2.imwrite(filename, cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
    #print(f"[INFO] Saved cropped image: {filename}")



# ------------------- Face Recognition Thread -------------------
def start_face_recognition_thread(photo_id):
    #print(f"[THREAD] Running face recognition for Person {photo_id}...")
    #run_face_recognition(photo_id)
    #print(f"[THREAD] Recognition complete for Person {photo_id}.")

    """Start face recognition in a separate thread."""
    thread = threading.Thread(target=run_face_recognition, args=(photo_id,), daemon=True)
    thread.start()
    return thread

# ------------------- Hourly Thread -------------------




# ------------------- Main Logic -------------------
if __name__ == "__main__":
    load_environment("./../data/.env.yolocam")

    import logging

    # Basic logger configuration
    logging.basicConfig(
        level=logging.INFO,                                # Log level
        format="%(asctime)s [%(levelname)s] %(message)s",  # Log message format
        handlers=[
            logging.FileHandler("app.log"),                # Log to a file named app.log
            logging.StreamHandler()                        # Also print logs to console
        ]
    )




    #load_dotenv(dotenv_path="./data/.env.yolocam")
    #load_dotenv(find_dotenv())

    # --- Load environment variables ---
    crypto = CryptoManager()
    RTSP_CREDENTIALS = crypto.decrypt(os.getenv("RTSP_CREDENTIALS"))
    RTSP_IPADDRESS = os.getenv("RTSP_IPADDRESS")
    RTSP_URL = f"rtsp://{RTSP_CREDENTIALS}@{RTSP_IPADDRESS}/cam/realmonitor?channel=1&subtype=0"

    _CAP_PROP_FRAME_WIDTH = int(os.getenv("CAP_PROP_FRAME_WIDTH", 2560))
    _CAP_PROP_FRAME_HEIGHT = int(os.getenv("CAP_PROP_FRAME_HEIGHT", 1440))
    _FRAME_TOP = int(os.getenv("FRAME_TOP", 100))
    _FRAME_BOTTOM = int(os.getenv("FRAME_BOTTOM", 1900))
    _FRAME_LEFT = int(os.getenv("FRAME_LEFT", 1075))
    _FRAME_RIGHT = int(os.getenv("FRAME_RIGHT", 1875))

    THERSHOLD_TOP_START_X = int(os.getenv("THERSHOLD_TOP_START_X", 50))
    THERSHOLD_TOP_START_Y = int(os.getenv("THERSHOLD_TOP_START_Y", 550))
    THERSHOLD_TOP_END_X = int(os.getenv("THERSHOLD_TOP_END_X", 1200))



    THERSHOLD_BOTTOM_START_X = int(os.getenv("THERSHOLD_BOTTOM_START_X", 50))
    THERSHOLD_BOTTOM_START_Y = int(os.getenv("THERSHOLD_BOTTOM_START_Y", 1100))
    THERSHOLD_BOTTOM_END_X = int(os.getenv("THERSHOLD_BOTTOM_END_X", 1200))






    limit_frame_count_no_human = int(os.getenv("LIMIT_FRAME_COUNT_NO_HUMANS", 10))
    min_frames_per_person = int(os.getenv("MIN_FRAMES_PER_PERSON", 5))
    max_frames_per_person = int(os.getenv("MAX_FRAMES_PER_PERSON", 20))

    # --- Initialize camera ---
    cap = cv2.VideoCapture(RTSP_URL)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, _CAP_PROP_FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, _CAP_PROP_FRAME_HEIGHT)

    print("Set resolution:",
          int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), "x",
          int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))

    _YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")
    detector = YOLOWorker(_YOLO_MODEL, conf=0.5).start()
    human_present = False
    frame_count_no_human = 0
    saved_frames = 0
    photo_id = None
    
    # Allow manual override via env var
    SHOW_WINDOW = os.getenv("SHOW_WINDOW", "false").lower() in ("1", "true", "yes")
    last_run_time = datetime.now() - timedelta(minutes=5)
    global last_hourly_run
    stop_requested = False
    while not stop_requested:
        ret, frame = cap.read()
        if not ret:
            continue

        # Periodically trigger background processing
        maybe_trigger_hourly_process()


        # Crop region of interest
        _frame = frame[_FRAME_TOP:_FRAME_BOTTOM, _FRAME_LEFT:_FRAME_RIGHT]
        current_time = datetime.now()
        
        # Calculate the difference between the current time and the last time we printed.
        time_difference = current_time - last_run_time
        if time_difference.total_seconds() >= 300:
            print(f"Working.. at date and time: {current_time}")
            # Reset the last_run_time to the current time.
            last_run_time = current_time

        detector.infer_async(_frame)
        result = detector.get_results()
        if result:
            _frame, _results = result
            if _results is None:
                continue

            # Access first result (since YOLO returns list)
            _result = _results[0]
            boxes = _result.boxes
            human_detected = False
            total_humans = 0

            for box in boxes:
                cls = int(box.cls)
                conf = float(box.conf)
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                if cls == 0 and conf > 0.5:  # Human class
                    total_humans += 1
                    human_detected = True
                    h = y2 - y1

                    # ---------------- Distance Estimation ----------------
                    if h > 600:
                        level = "Very Close"
                        color = (0, 255, 0)
                    elif h > 400:
                        level = "Medium"
                        color = (0, 255, 255)
                    else:
                        level = "Far"
                        color = (0, 0, 255)

                    # Draw bounding box
                    cv2.rectangle(_frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(_frame, f"{level} ({h}px)",
                                (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    #cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)
                    # -------------- Save if level > Medium --------------
                    if cy > THERSHOLD_TOP_START_Y and cy < THERSHOLD_BOTTOM_START_Y:  # Medium or Very Close
                        if not human_present:
                            photo_id = datetime.now().strftime("%y%m%d%H%M%S%f")[:-3]
                            saved_frames = 0
                            human_present = True

                        if saved_frames < max_frames_per_person:
                            
                            save_frame(frame, photo_id, saved_frames + 1, total_humans,
           _FRAME_TOP, _FRAME_BOTTOM, _FRAME_LEFT, _FRAME_RIGHT)
                            saved_frames += 1

                            if saved_frames == max_frames_per_person:
                                start_face_recognition_thread(photo_id)

            # -------------- Handle no humans --------------
            if not human_detected:
                frame_count_no_human += 1
                if human_present and frame_count_no_human >= limit_frame_count_no_human:
                    human_present = False
                    frame_count_no_human = 0
            else:
                frame_count_no_human = 0

             # Display info
            cv2.putText(_frame, f"Humans Detected: {total_humans}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)  
                     
            cv2.line(_frame, (THERSHOLD_TOP_START_X, THERSHOLD_TOP_START_Y), (THERSHOLD_TOP_END_X, THERSHOLD_TOP_START_Y), (0, 0, 255), 2)
            cv2.line(_frame, (THERSHOLD_BOTTOM_START_X, THERSHOLD_BOTTOM_START_Y), (THERSHOLD_BOTTOM_END_X, THERSHOLD_BOTTOM_START_Y), (0, 0, 255), 2)
            _frame = cv2.resize(_frame, (1000, 800))
            if SHOW_WINDOW:
                cv2.imshow("YOLOv8 Human Detection", _frame)




        _frame = cv2.resize(_frame, (1000, 800))
        cv2.line(_frame, (THERSHOLD_TOP_START_X, THERSHOLD_TOP_START_Y), (THERSHOLD_TOP_END_X, THERSHOLD_TOP_START_Y), (0, 0, 255), 2)
        cv2.line(_frame, (THERSHOLD_BOTTOM_START_X, THERSHOLD_BOTTOM_START_Y), (THERSHOLD_BOTTOM_END_X, THERSHOLD_BOTTOM_START_Y), (0, 0, 255), 2)
        if SHOW_WINDOW:
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                stop_requested = True
        time.sleep(0.03)

    # --- Cleanup ---
    cap.release()
    detector.stop()
    cv2.destroyAllWindows()
