# Guest Registration
   ## Video Registration
      - Unique gmail id 
   ## Initate Guest
   - Guest will now be able to get auto month due raised.
   - Email alert sent.. Welcome..
   - Active status




# WH Face Detection

This project provides a face detection and attendance system using deep learning models (YOLO and SSD) and a simple database for logging attendance. It is designed for use in environments like the White House, but can be adapted for other organizations.

## Features
- Face detection in images and video using YOLOv8 and SSD models
- Attendance logging to a CSV file and SQLite database
- Organized image storage for detected persons
- Easy-to-use scripts for adding new faces and running detection


## Pre rec
-make-4.1.1-windows-x86_64.msi
-make sure you are having above msi install to avoid cmake error


## Project Structure
- `app/` - Main application code
  - `main.py` - Entry point for running the app
  - `database.py`, `dbOutput.py`, `dbscript.py` - Database utilities
  - `face-detection-master/` - Face detection scripts and notebooks
- `images/` - Source images for face detection
- `./../detected_persons/` - Images of detected persons
- `requirements.txt` - Python dependencies
- `attendance_log.csv` - Attendance records
- `WhiteHouse.db` - SQLite database

## Setup
1. Clone the repository:
   ```powershell
   git clone https://github.com/writeforsajid/WH-Face-Detection.git
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Run the main application:
   ```powershell
   python app/main.py
   ```

## Usage
- To detect faces in images or video, use the scripts in `app/face-detection-master/`.
- To add new faces, use the provided notebook or scripts.
- Attendance is automatically logged in `attendance_log.csv` and `WhiteHouse.db`.

## Models
- YOLOv8 models (`yolov8m.pt`, `yolov8n.pt`)
- SSD model (`res10_300x300_ssd_iter_140000.caffemodel`, `deploy.prototxt`)

## Contributing
Feel free to fork the repository and submit pull requests for improvements or new features.

## License
This project is licensed under the MIT License.


git add .  # stage all files
git commit -m "commit"


git filter-repo --force --path yolo_cam/media --invert-paths


Force fully removed and Push cleaned history to GitHub
git remote add origin https://github.com/writeforsajid/WH-Face-Detection.git
git remote -v
git branch
git checkout WH-Face-Detection-V1
git push origin WH-Face-Detection-V1 --force


docker-compose build

## build and run the environment
D:\WH-Face-Detection\webapp\_venv\Scripts\Activate.ps1
## to run the app
uvicorn main:app --reload

uvicorn main:app --reload --host 127.0.0.1 --port 8000 --ssl-keyfile="webapp.key" --ssl-certfile="webapp.crt"


