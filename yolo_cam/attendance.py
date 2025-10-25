# attendance.py
import cv2, face_recognition, time, os, csv, numpy as np
print("imported")
# from pathlib import Path

# # CONFIG
# VIDEO_SOURCE = 0  # 0 for webcam, or "rtsp://..." for IP cam
# DETECTOR_PROTO = "deploy.prototxt"   # download res10_300x300_ssd_deploy.prototxt
# DETECTOR_MODEL = "res10_300x300_ssd_iter_140000.caffemodel"
# ATTENDANCE_CSV = "attendance_log.csv"
# TOLERANCE = 0.5           # lower = stricter. face_recognition default ~0.6
# DEDUPE_SECONDS = 60       # don't re-log same person within this window

# # Load OpenCV DNN face detector (fast)
# net = cv2.dnn.readNetFromCaffe(DETECTOR_PROTO, DETECTOR_MODEL)
# #KNOWN_DIR = Path("images") / "Known"

# # Get all .jpg files
# #image_files = list(KNOWN_DIR.glob("*.jpg"))
# # Load known faces: expects folder "known/<name>/*.jpg"
# #KNOWN_DIR = Path("images\Known\*.jpg")
# known_encodings = []
# known_names = []
# BASE_DIR = Path(__file__).resolve().parent

# # Known faces folder
# KNOWN_DIR = BASE_DIR / "images"

# # all jpgs
# image_files = list(KNOWN_DIR.glob("*.jpg"))

# for person_dir in KNOWN_DIR.iterdir():
#     if not person_dir.is_dir(): continue
#     name = person_dir.name
#     for img_path in person_dir.glob("*"):
#         img = face_recognition.load_image_file(str(img_path))
#         encs = face_recognition.face_encodings(img)
#         if len(encs) == 0:
#             print(f"WARNING: no face in {img_path}")
#             continue
#         known_encodings.append(encs[0])
#         known_names.append(name)

# print("Loaded known faces:", set(known_names))

# # Prepare video
# cap = cv2.VideoCapture(VIDEO_SOURCE)
# last_seen = {}  # name -> last timestamp

# # Prepare CSV
# first_write = not os.path.exists(ATTENDANCE_CSV)
# csvf = open(ATTENDANCE_CSV, "a", newline="")
# writer = csv.writer(csvf)
# if first_write:
#     writer.writerow(["timestamp", "name", "confidence", "camera"])  # header

# def detect_faces_opencv_dnn(frame):
#     (h, w) = frame.shape[:2]
#     blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300,300)), 1.0,
#                                  (300,300), (104.0, 177.0, 123.0))
#     net.setInput(blob)
#     detections = net.forward()
#     rects = []
#     for i in range(0, detections.shape[2]):
#         conf = detections[0,0,i,2]
#         if conf < 0.5: continue
#         box = detections[0,0,i,3:7] * np.array([w,h,w,h])
#         (startX, startY, endX, endY) = box.astype("int")
#         # bound check
#         startX, startY = max(0,startX), max(0,startY)
#         endX, endY = min(w-1,endX), min(h-1,endY)
#         rects.append((startX,startY,endX,endY, float(conf)))
#     return rects

# print("Starting video. Press q to quit.")
# while True:
#     breakpoint
#     ret, frame = cap.read()
#     if not ret:
#         print("Failed to grab frame")
#         break

#     # Optional: resize for speed
#     small = cv2.resize(frame, (0,0), fx=0.5, fy=0.5)
#     scale = frame.shape[1] / small.shape[1]

#     rects = detect_faces_opencv_dnn(small)
#     names_on_frame = []

#     for (sx, sy, ex, ey, conf) in rects:
#         # rescale back to original
#         sxi, syi = int(sx*scale), int(sy*scale)
#         exi, eyi = int(ex*scale), int(ey*scale)
#         face_img = frame[syi:eyi, sxi:exi]
#         # skip tiny faces
#         if face_img.shape[0] < 20 or face_img.shape[1] < 20:
#             continue

#         # Use face_recognition to find embedding (convert BGR->RGB)
#         rgb_face = face_img[:, :, ::-1]
#         enc = face_recognition.face_encodings(rgb_face)
#         if len(enc) == 0:
#             # fallback: compute encoding from full frame location
#             enc_full = face_recognition.face_encodings(frame, [(syi, exi, eyi, sxi)])
#             if len(enc_full) == 0:
#                 continue
#             enc = enc_full

#         enc = enc[0]
#         # compare with knowns
#         dists = face_recognition.face_distance(known_encodings, enc)
#         if len(dists) > 0:
#             best_idx = np.argmin(dists)
#             best_dist = dists[best_idx]
#             if best_dist <= TOLERANCE:
#                 name = known_names[best_idx]
#                 confidence = 1.0 - best_dist  # rough
#             else:
#                 name = "Unknown"
#                 confidence = 1.0 - best_dist
#         else:
#             name = "Unknown"
#             confidence = 0.0

#         # Dedup and log attendance
#         now = time.time()
#         if name != "Unknown":
#             last = last_seen.get(name, 0)
#             if now - last > DEDUPE_SECONDS:
#                 ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
#                 writer.writerow([ts, name, f"{confidence:.3f}", VIDEO_SOURCE])
#                 csvf.flush()
#                 last_seen[name] = now
#                 print(f"[{ts}] Logged {name} conf={confidence:.3f}")

#         # draw box + label
#         cv2.rectangle(frame, (sxi, syi), (exi, eyi), (0,255,0), 2)
#         cv2.putText(frame, f"{name} {confidence:.2f}", (sxi, syi-10),
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

#     cv2.imshow("Attendance", frame)
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break

# cap.release()
# csvf.close()
# cv2.destroyAllWindows()
