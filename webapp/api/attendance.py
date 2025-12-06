from fastapi import APIRouter, HTTPException,Query
from services import attendance_service
from typing import Optional
from datetime import date
from datetime import datetime
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

@router.get("/records")
def get_attendance_records(
    guest_id: str = Query(..., description="ID of the guest"),
    role_name:str = Query(...,description="Role name of the guest"),
    start_date: str = Query(..., description="Start date in YYYY-MM-DD"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Records per page"),
):
    """
    Fetch attendance records between given dates with pagination.
    """

    try:
        start_date = datetime.fromisoformat(start_date).date()
        end_date = datetime.fromisoformat(end_date).date()
        result = attendance_service.fetch_attendance(guest_id, role_name, start_date, end_date, page, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Attendance data not found")
    return result

@router.get("/guest_logs")
def get_guest_logs(
    guest_id: str = Query(..., description="ID of the guest")
):
    """
    Fetch recent device-level logs for a guest.
    Returns array of objects with keys: Device, Entry, Exit
    """
    try:

        result = attendance_service.get_guest_device_logs(guest_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Return empty list if no results rather than 404 to make frontend simpler
    return result or []