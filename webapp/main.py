from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import json

# Import routers
from api import  reports,guests,upload_video,attendance,employees
from api import beds as beds_router
from api import auth as auth_router
from db import database
from dotenv import load_dotenv, find_dotenv
from utilities.environment_variables import load_environment
import os
#load_dotenv(dotenv_path="./data/.env.webapp")

#load_environment("../data/.env.webapp");
load_environment("./../data/.env.webapp")
#load_dotenv(find_dotenv())

API_IPADDRESS=os.getenv("API_IPADDRESS")
if API_IPADDRESS is None: API_IPADDRESS = "http://127.0.0.1:8000"

API_LOCALHOST=os.getenv("API_LOCALHOST")
if API_LOCALHOST is None: API_LOCALHOST = "http://localhost:8000"


# Import routers


app = FastAPI(title="Face Detection Project", version="1.0")


origins = [
    API_IPADDRESS,
    API_LOCALHOST,
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5501",
    "http://127.0.0.1:5501",
    "*"  # Allow all origins for development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers

app.include_router(auth_router.router, prefix="/auth", tags=["Auth"])
app.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
app.include_router(guests.router, prefix="/guests", tags=["Guests"])
app.include_router(employees.router, prefix="/employees", tags=["Employees"])
app.include_router(guests.router, prefix="/login", tags=["login"])
app.include_router(upload_video.router, prefix="/video", tags=["Video Upload"])
app_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(app_dir, "static")
#videos_dir=os.path.join(app_dir,"../data/videos")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
#app.mount("/videos", StaticFiles(directory=videos_dir), name="videos")




app.include_router(reports.router, tags=["Reports"])
app.include_router(reports.router, prefix="/reports",tags=["Reports"])
app.include_router(auth_router.router)
app.include_router(beds_router.router, prefix="/beds", tags=["Beds"])



# Startup / Shutdown Events
@app.on_event("startup")
async def startup():
    database.init_db()  # Create tables if not exists

@app.get("/")
def root():
    return {"message": "Welcome to Face Detection API"}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/faq", response_class=HTMLResponse)
def faq():
    """Return the FAQ page with the FAQ JSON embedded into the page.

    This endpoint reads the static `faq_section.html` fragment and the JSON
    file `static/Json/faq_questions.json` and returns a full HTML page that
    includes the static CSS/JS and an embedded `window.FAQ_DATA` variable
    so the client-side script can render without a secondary fetch.
    """
    try:
        # static_dir is defined above as the path to webapp/static
        faq_fragment_path = os.path.join(static_dir, 'faq_section.html')
        faq_json_path = os.path.join(static_dir, 'Json', 'faq_questions.json')

        with open(faq_fragment_path, 'r', encoding='utf-8') as f:
            fragment = f.read()

        with open(faq_json_path, 'r', encoding='utf-8') as f:
            faq_json_text = f.read()

        # Build a minimal HTML document that links the same static assets
        html = (
            '<!doctype html>\n'
            '<html lang="en">\n'
            '<head>\n'
            '  <meta charset="utf-8">\n'
            '  <meta name="viewport" content="width=device-width,initial-scale=1">\n'
            '  <title>FAQ</title>\n'
            '  <link rel="stylesheet" href="/static/css/faq_section.css">\n'
            '</head>\n'
            '<body>\n'
            f'{fragment}\n'
            f'<script>window.FAQ_DATA = {faq_json_text};</script>\n'
            '<script src="/static/js/faq_section.js"></script>\n'
            '</body>\n'
            '</html>'
        )
        return HTMLResponse(content=html, status_code=200)
    except Exception as e:
        return HTMLResponse(content=f"<pre>Failed to render FAQ: {e}</pre>", status_code=500)


