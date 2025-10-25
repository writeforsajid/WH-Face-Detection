from fastapi import APIRouter, HTTPException
from services import attendance_service

router = APIRouter()

@router.post("/")
def mark_attendance(data: dict):
    try:
        result = attendance_service.mark_attendance(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Guest not found")
    return result

@router.get("/")
def get_attendance():
    return attendance_service.get_attendance()
