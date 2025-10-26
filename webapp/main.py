from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from api import  reports,guests,upload_video
from api import beds as beds_router
from static import auth as auth_router
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

app.include_router(guests.router, prefix="/guests", tags=["Guests"])
app.include_router(upload_video.router, prefix="/video", tags=["Video Upload"])
app_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(app_dir, "static")
#videos_dir=os.path.join(app_dir,"../data/videos")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
#app.mount("/videos", StaticFiles(directory=videos_dir), name="videos")




app.include_router(reports.router, tags=["Reports"])
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


