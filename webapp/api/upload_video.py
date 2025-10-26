from fastapi import APIRouter, UploadFile, Form
from fastapi.responses import JSONResponse
from services.video_service import save_uploaded_video

router = APIRouter()

@router.post("/upload_video")
async def upload_video_endpoint(file: UploadFile, guest_name: str = Form(None),guest_type: str = Form(None),comment: str = Form(None),email: str = Form(None),phone: str = Form(None)):
    """
    Accepts a video file (Blob) and saves it to /data/videos.
    Returns file info and storage path.
    """
    return await save_uploaded_video(file, guest_name,guest_type,comment,email,phone)
    #return JSONResponse(result)
    
