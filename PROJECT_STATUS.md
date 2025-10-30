# WH Face Detection — Project Status and Remaining Work

This document summarizes the current state of the WH Face Detection project and lists remaining work, priorities, and rough estimates to finish or improve the project.

## Quick project overview
- Codebase: FastAPI webapp under `webapp/` with SQLite DB (`data/WhiteHouse.db`).
- Models: YOLOv8 weights are present in `yolo_cam/` and repository root (`yolov8n.pt`), and an SSD model (`res10_300x300_ssd_iter_140000.caffemodel`) and `deploy.prototxt` are present.
- Primary features implemented (core working pieces):
  - FastAPI app in `webapp/main.py` with routers for guests, auth, reports, beds and video upload.
  - Local SQLite DB and initialization in `webapp/db/database.py` (creates tables & seeds beds/roles).
  - Video upload handling and local storage in `webapp/services/video_service.py` (saves videos and JSON metadata).
  - Simple face detector utility in `webapp/detector.py` using OpenCV Haar cascades (works for image-based face location).
  - Background worker scaffolding in `webapp/services/face_worker.py` (currently mostly commented out).
  - Authentication routes in `webapp/api/auth.py` and session management using `guest_sessions` table.
  - Some tests in `tests/` (a schema/insert test).

## What appears to be completed / usable now
- API skeleton and many endpoints are implemented (guests, auth, video upload, reports).
- Database schema is comprehensive (guests, guest_auth, guest_sessions, attendance, beds, guest_beds, roles, etc.).
- Video upload pipeline saves video files and JSON metadata to `data/Videos` and places a preview copy under `webapp/static/temp/preview.webm`.
- Basic static front-end exists under `webapp/static/` (templates and JS/CSS).

## Key gaps and remaining work (detailed)
Below are concrete missing pieces or improvements grouped by priority.

### High priority
1) Fix authentication security (1 day)
   - Problem: `api/auth.py` currently verifies login against `guests.password` plain-text field; the project already stores password hashes in `guest_auth.password_hash`. Login should verify the hashed password using `guest_auth` only.
   - Impact: Security vulnerability and inconsistent auth flow.
   - Action: Update `login` to use `guest_auth.password_hash`, remove or stop storing plaintext `password` in `guests` table, migrate existing accounts or add a migration path.

2) Implement face recognition and attendance marking (3-7 days)
   - Problem: `face_worker.py` contains commented-out code and `video_service.save_uploaded_video` only stores files and a JSON. There's no active pipeline that extracts frames/encodings and persists face vectors for matching.
   - Action: Integrate a face-encoding pipeline (options below), save encodings to `guest_faces` table (or a new table), implement an attendance-match endpoint that receives an image/frame and returns guest match and marks attendance.
   - Options & notes:
     - Use python `face_recognition` (dlib-based) for quick prototype (good accuracy). Pros: easy. Cons: dlib binary dependencies / build complexity on some platforms.
     - Use a neural embedding model (e.g., a lightweight face encoder packaged with PyTorch / ONNX). This can align better with YOLO detection.
     - For detection, keep using Haar cascade or integrate YOLOv8 from `yolo_cam/` for object detection then crop faces and encode.

3) Enable/complete background video processing (2 days)
   - Problem: `face_worker.process_guest_video_async` exists but is not called and its implementation is commented.
   - Action: Hook `save_uploaded_video` to call the async worker (or schedule via Celery/RQ) and implement the frame extraction / encoding logic.

4) Add input validation and size/format checks for uploads (0.5 day)
   - Add file size limits, allowed MIME types, and streaming-saves to avoid OOM on large uploads.

### Medium priority
5) Tests & CI (2-4 days)
   - Problem: Only one basic test exists. No CI configured.
   - Action: Add pytest tests for key services (`video_service`, `guest_service`, DB init), add GitHub Actions workflow to run tests and flake8/black.

6) Documentation & run instructions (this document + README improvements) (0.5 day)
   - Problem: README exists but is generic and outdated in parts.
   - Action: Add this file and a clear `webapp/README.md` with environment variables, how to run locally, and Docker instructions.

7) Integrate YOLO pipeline (optional but useful) (2-4 days)
   - `yolo_cam/` contains runners and models. Integrate them either as a separate microservice or a callable module to detect faces/people in video streams.

### Low priority / polish
8) Remove large model files from repository and add to releases or storage (0.5 day)
   - `yolov8n.pt` and similar are large. Add them to `.gitignore` and use a download-on-demand script.

9) Static frontend improvements and sample pages (1-2 days)
   - Improve the HTML templates, add login flow examples that use the `/auth` endpoints, and wire attendance pages.

10) Database migrations (1-2 days)
    - Add a migration tool (Alembic or simple SQL migration scripts) to handle schema changes instead of dynamic `CREATE TABLE IF NOT EXISTS`.

11) Secrets and environment handling (0.5 day)
    - Document `.env.webapp` format and required variables. Ensure secrets aren’t checked into source.

## Small bugfixes & code smells (quick wins)
- Ensure `webapp/services/video_service.py` uses secure filename handling and avoids path traversal.
- In `webapp/main.py`, consider removing the wildcard CORS allow_origins in production.
- In `db/database.py`, confirm DB_PATH resolution is robust to running from other working directories.
- Improve exception handling & logging for background workers.

## Suggested small PRs (bite-sized tasks)
- PR-001: Fix login to use hashed passwords (1 day).
- PR-002: Wire `save_uploaded_video` to call `process_guest_video_async` and enable the basic worker to save 3 encodings per guest (1–2 days).
- PR-003: Add input validation to upload endpoint (0.5 day).
- PR-004: Add a GitHub Actions workflow that runs pytest (1 day).
- PR-005: Add a `scripts/download_models.py` script and `.gitignore` patterns for model files (0.5 day).

## Run / dev instructions (Windows PowerShell)
1) Activate the virtual environment (if using the included `webapp/_venv`)

```powershell
# In PowerShell
& "${PWD}\webapp\_venv\Scripts\Activate.ps1"
```

2) Install requirements (if you create a new venv)

```powershell
pip install -r webapp/requirements.txt
```

3) Set environment variables (example `.env.webapp` expected in `data/`)
- `DB_PATH` (default `./data/WhiteHouse.db`)
- `VIDEOS_PATH` (default `./data/Videos`)
- `STATIC_TEMP_PATH` (default `./webapp/static/temp`)

4) Run the FastAPI app locally

```powershell
cd webapp
# development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

5) Run tests

```powershell
# from repo root
pytest -q
```

## Environment & dependencies
- Core requirements are listed in `webapp/requirements.txt` (FastAPI, uvicorn, SQLAlchemy, python-multipart, pydantic[email], python-dotenv, passlib/cryptography for password handling).
- Optional heavy dependencies for face recognition: `face_recognition` (dlib), `torch`/`torchvision`, or OpenVINO/ONNX runtime if using alternative encoders.

## Next steps & recommended priorities (short roadmap)
1. Fix auth (secure hashing + remove plaintext) — high
2. Implement & enable background video processing to create face encodings — high
3. Implement matching endpoint to mark attendance from an image/frame — high
4. Add tests + CI — medium
5. Integrate YOLOv8 detector if higher-quality detection needed — medium
6. Improve docs, env handling, and remove large models from git — low

## Notes / Assumptions made while analyzing the repo
- I examined `webapp/` files such as `main.py`, `detector.py`, `db/database.py`, `services/*`, and API routes.
- I did not run the code during this analysis. Some runtime issues (missing packages, native build deps for dlib) may appear when executing.

---
If you'd like, I can now:
- Create a `webapp/README.md` with run instructions and environment variable examples.
- Implement the quick PR to fix authentication (update `login` to use hashed passwords and migrate or ignore plaintext passwords).
- Wire the video upload to start the background worker and implement a minimal face-encoding pipeline (prototype using `face_recognition`).

Tell me which next step you want me to take and I'll start it and update the todo list accordingly.