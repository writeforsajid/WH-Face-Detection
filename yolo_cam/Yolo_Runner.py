from dotenv import load_dotenv, find_dotenv
from ultralytics import YOLO


import cv2, threading, queue, time, datetime, os
import numpy as np
import sys
from master_faces import thread_video_process
from datetime import datetime, timedelta



# Add parent directory for utilities
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from face_recognition_worker import run_face_recognition,get_unprocessed_file_id
from utilities.crypto_manager import CryptoManager
from utilities.environment_variables import load_environment

PROCESS_INTERVAL_HOURS = 1   # production
DEV_MODE = True              # ✅ switch to True for testing

if DEV_MODE:
    PROCESS_INTERVAL_HOURS = 0.04  # ~3 minutes for testing

#last_process_time_face_recognition = datetime.min

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






# IOU helper to compare boxes
def iou(boxA, boxB):
    # box: (x1, y1, x2, y2)
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interW = max(0, xB - xA)
    interH = max(0, yB - yA)
    interArea = interW * interH
    boxAArea = max(1, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(1, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))
    return interArea / float(boxAArea + boxBArea - interArea + 1e-6)

# Semaphore to limit concurrent recognition threads (change value to desired concurrency)
RECOG_THREAD_SEM = threading.Semaphore(2)


def thread_face_recognition_process():
    # global last_process_time_face_recognition
    # now = datetime.now()
    # if now - last_process_time_face_recognition >= timedelta(hours=PROCESS_INTERVAL_HOURS):
    #     last_process_time_face_recognition = now
        fileid=get_unprocessed_file_id(OT)
        if fileid is not None:
            threaded_start_face_recognition(fileid)


def threaded_start_face_recognition(photo_id):
    # wrapper to limit concurrency
    def _worker(pid):
        try:
            run_face_recognition(pid)
        finally:
            RECOG_THREAD_SEM.release()

    # acquire if possible else skip starting new thread instantly (prevents too many)
    acquired = RECOG_THREAD_SEM.acquire(blocking=False)
    if not acquired:
        # If semaphore not available, start thread anyway but queued later would be better.
        # To keep simple, skip if too many threads. You can also block with timeout.
        print(f"[WARN] Max recognition threads busy. Skipping start for {photo_id}")
        return None
    t = threading.Thread(target=_worker, args=(photo_id,), daemon=True)
    t.start()
    return t

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




    NO_HUMAN_FRAMES_TO_END = limit_frame_count_no_human  # reuse your var
    # --- Event & tracking variables (initialize before loop) ---
    previous_total_humans = 0
    event_active = False
    event_id = None
    event_count = 0
    EVENT_WINDOW_START = datetime.min
    EVENT_COOLDOWN = timedelta(seconds=60)
    MAX_EVENTS_PER_PERIOD = 3
    EVENT_PERIOD = timedelta(minutes=1)
    previous_boxes = []  # Track each person's box and captures in current event
    no_human_frames = 0
    # --- Main Loop ---
    while not stop_requested:
        ret, frame = cap.read()
        if not ret or frame is None or frame.size == 0:
            continue

        thread_video_process()
        #thread_face_recognition_process()
        # Only run face recognition when no active event (no humans present)
        if not event_active:
            thread_face_recognition_process()
        cv2.rectangle(frame, (_FRAME_LEFT,_FRAME_TOP ), ( _FRAME_RIGHT,_FRAME_BOTTOM), (255,0,255), 2)
        _frame = frame[_FRAME_TOP:_FRAME_BOTTOM, _FRAME_LEFT:_FRAME_RIGHT]
        current_time = datetime.now()

        # Periodic heartbeat
        if (current_time - last_run_time).total_seconds() >= 300:
            print(f"[INFO] Working at: {current_time}")
            last_run_time = current_time

        # YOLO inference
        detector.infer_async(_frame)
        result = detector.get_results()
        total_humans = 0
        human_detected = False
        person_boxes = []

        if result:
            _frame_from_worker, _results = result
            _frame = _frame_from_worker
            if _results:
                _result = _results[0]
                boxes = _result.boxes

                # Collect human boxes
                for box in boxes:
                    cls = int(box.cls)
                    conf = float(box.conf)
                    if cls == 0 and conf > 0.5:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        person_boxes.append((x1, y1, x2, y2))
                total_humans = len(person_boxes)
                human_detected = total_humans > 0

        # --- EVENT START detection ---
        now = datetime.now()
        # Reset event window if expired
        if now - EVENT_WINDOW_START > EVENT_PERIOD:
            EVENT_WINDOW_START = now
            event_count = 0

        # Start event only if at least one human is inside vertical band
        person_in_band = any(THERSHOLD_TOP_START_Y < int((y1 + y2) / 2) < THERSHOLD_BOTTOM_START_Y
                            for (x1, y1, x2, y2) in person_boxes)

        if person_in_band and not event_active:
            if event_count < MAX_EVENTS_PER_PERIOD or now - EVENT_WINDOW_START > EVENT_PERIOD:
                event_active = True
                event_id = datetime.now().strftime("%y%m%d%H%M%S%f")[:-3]
                event_count += 1
                previous_boxes = []
                no_human_frames = 0
                print(f"[EVENT] Started {event_id} — human entered target zone.")

        # --- EVENT PROCESSING ---
        if event_active:
            for (x1, y1, x2, y2) in person_boxes:
                cy = int((y1 + y2) / 2)

                # Only capture if inside band
                if not (THERSHOLD_TOP_START_Y < cy < THERSHOLD_BOTTOM_START_Y):
                    cv2.rectangle(_frame, (x1, y1), (x2, y2), (100, 100, 100), 1)
                    continue

                # Match with previous boxes by IOU
                matched = None
                best_iou = 0
                for pb in previous_boxes:
                    i = iou((x1, y1, x2, y2), pb["box"])
                    if i > best_iou:
                        best_iou = i
                        matched = pb

                now = datetime.now()
                if matched and best_iou > 0.6:
                    matched["last_seen"] = now
                    if matched["saved"] < max_frames_per_person:
                        last_saved_ts = matched.get("last_saved_ts", datetime.min)
                        if (now - last_saved_ts).total_seconds() > 0.5:
                            matched["saved"] += 1
                            matched["last_saved_ts"] = now
                            save_frame(frame, matched["photo_id"], matched["saved"], total_humans,
                                    _FRAME_TOP, _FRAME_BOTTOM, _FRAME_LEFT, _FRAME_RIGHT)
                            print(f"[CAPTURE] Frame {matched['saved']} for {matched['photo_id']}")
                else:
                    # New person
                    new_photo_id = f"{event_id}_{len(previous_boxes)+1}"
                    new_entry = {
                        "box": (x1, y1, x2, y2),
                        "saved": 1,
                        "photo_id": new_photo_id,
                        "first_seen": now,
                        "last_seen": now,
                        "last_saved_ts": now
                    }
                    previous_boxes.append(new_entry)
                    save_frame(frame, new_photo_id, 1, total_humans,
                            _FRAME_TOP, _FRAME_BOTTOM, _FRAME_LEFT, _FRAME_RIGHT)
                    print(f"[CAPTURE] Initial frame for {new_photo_id}")

                # Draw box + distance info
                h = y2 - y1
                if h > 600: level, color = "Very Close", (0,255,0)
                elif h > 400: level, color = "Medium", (0,255,255)
                else: level, color = "Far", (0,0,255)
                cv2.rectangle(_frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(_frame, f"{level} {h}px", (x1, y1-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # --- EVENT END detection ---
        if not human_detected and event_active:
            no_human_frames += 1
            if no_human_frames >= NO_HUMAN_FRAMES_TO_END:
                print(f"[EVENT] Ending {event_id}, launching recognition for {len(previous_boxes)} persons")
                for pb in previous_boxes:
                    if pb["saved"] >= min_frames_per_person:
                        threaded_start_face_recognition(pb["photo_id"])
                event_active = False
                event_id = None
                previous_boxes = []
                no_human_frames = 0
        else:
            if human_detected:
                no_human_frames = 0

        previous_total_humans = total_humans

        # --- DISPLAY ---
        cv2.putText(_frame, f"Humans: {total_humans}", (20,40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)
        cv2.line(_frame, (THERSHOLD_TOP_START_X, THERSHOLD_TOP_START_Y),
                (THERSHOLD_TOP_END_X, THERSHOLD_TOP_START_Y), (0,0,255), 2)
        cv2.line(_frame, (THERSHOLD_BOTTOM_START_X, THERSHOLD_BOTTOM_START_Y),
                (THERSHOLD_BOTTOM_END_X, THERSHOLD_BOTTOM_START_Y), (0,0,255), 2)
        
        if _frame is not None and _frame.size != 0:
            _frame = cv2.resize(_frame, (1000,800))
            if SHOW_WINDOW:
                cv2.imshow("YOLOv8 Human Detection (Event)", _frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    stop_requested = True

        time.sleep(0.03)

# --- Cleanup ---
cap.release()
detector.stop()
cv2.destroyAllWindows()
