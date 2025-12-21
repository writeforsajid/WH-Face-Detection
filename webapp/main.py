from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
import uvicorn
import json
import os


# Load environment variables
from utilities.environment_variables import load_environment
load_environment("./../data/.env.webapp")

API_LOCALHOST = os.getenv("API_LOCALHOST", "https://localhost:8000")

app = FastAPI(title="Face Detection Project", version="1.0")

# Force HTTPS to avoid mixed-content errors
app.add_middleware(HTTPSRedirectMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For PROD you can restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =======================
# STATIC FILES FIX
# =======================

# Force static directory path to the container location
STATIC_DIR = "/app/static"
def is_docker():
    return os.path.exists("/.dockerenv")

# Set static directory
if is_docker():
    STATIC_DIR = "/app/static"
else:
    # Local Windows development path
   
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    STATIC_DIR = os.path.join(BASE_DIR, "static")

# Validate path
if not os.path.exists(STATIC_DIR):
    print("❌ Static directory NOT found:", STATIC_DIR)
else:
    print("✔ Static directory loaded:", STATIC_DIR)

# Then mount
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# =======================
# Routers
# =======================
from api import reports, guests, upload_video, attendance, employees
from api import metadata as metadata_router
from api import beds as beds_router
from api import auth as auth_router
from api import syst as syst_router
from api import leave as leave_router
from api import rentalmonth as rentalmonth_router
from scheduler import scheduler as scheduler_router
from db import database

app.include_router(leave_router.router, prefix="/leave", tags=["Leave"])
app.include_router(syst_router.router, prefix="/system", tags=["System"])
app.include_router(auth_router.router, prefix="/auth", tags=["Auth"])
app.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
app.include_router(guests.router, prefix="/guests", tags=["Guests"])
app.include_router(employees.router, prefix="/employees", tags=["Employees"])
app.include_router(upload_video.router, prefix="/video", tags=["Video Upload"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
app.include_router(beds_router.router, prefix="/beds", tags=["Beds"])
app.include_router(rentalmonth_router.router, prefix="/rentalmonth", tags=["RentalMonths"])
app.include_router(metadata_router.router, tags=["Metadata"])

# =======================
# Startup / Shutdown
# =======================
@app.on_event("startup")
async def startup():
    database.init_db()
    scheduler_router.start_scheduler()
    
@app.get("/")
def root():
    return {"message": "Welcome to Face Detection API"}

@app.get("/health")
def health():
    return {"status": "ok"}

# =======================
# FAQ Endpoint
# =======================
@app.get("/faq", response_class=HTMLResponse)
def faq():
    try:
        faq_html = os.path.join(STATIC_DIR, "faq_section.html")
        faq_json = os.path.join(STATIC_DIR, "Json", "faq_questions.json")

        with open(faq_html, "r", encoding="utf-8") as f:
            fragment = f.read()

        with open(faq_json, "r", encoding="utf-8") as f:
            faq_data = f.read()

        html = (
            "<!doctype html><html><head>"
            '<meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>FAQ</title>'
            '<link rel="stylesheet" href="/static/css/faq_section.css">'
            "</head><body>"
            f"{fragment}"
            f"<script>window.FAQ_DATA = {faq_data};</script>"
            '<script src="/static/js/faq_section.js"></script>'
            "</body></html>"
        )

        return HTMLResponse(content=html)
    except Exception as e:
        return HTMLResponse(content=f"<pre>Failed to render FAQ: {e}</pre>", status_code=500)


if __name__ == "__main__":
    if is_docker():
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8443,
            ssl_keyfile="certs/key.pem",
            ssl_certfile="certs/cert.pem"
        )
    else:
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=8000
        )
