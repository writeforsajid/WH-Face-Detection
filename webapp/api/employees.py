from fastapi import APIRouter, HTTPException, Query, Header,Form
from typing import Optional, Dict
from db.database import get_connection
from services import employee_service
from datetime import date,datetime, timezone

router = APIRouter()


def _require_token(auth_header: Optional[str]) -> str:
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return auth_header.split(" ", 1)[1].strip()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _validate_session(token: str) -> str:
    """Validate session token; return guest_id if valid else raise 401."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        now_iso = _iso(_now_utc())
        cur.execute(
            """
            SELECT gs.guest_id
            FROM guest_sessions gs
            WHERE gs.session_id = ?
              AND IFNULL(gs.revoked, 0) = 0
              AND gs.expires_at > ?
            """,
            (token, now_iso),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return row[0]
    finally:
        conn.close()



@router.get("/")
def list_employees(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by guest name"),
    status: Optional[str] = Query(
        None,
        description="Filter by status: active|inactive|closed",
        regex="^(active|inactive|closed)$",
    ),
):
    return employee_service.get_employees(page=page, limit=limit, search=search, status=status)















@router.get("/active")
def get_active_employee():
    """
    Fetch attendance records between given dates with pagination.
    """
 
    try:
        result = employee_service.get_active_employee()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Attendance data not found")
    return result


@router.post("/add_metadata")
def add_guest_metadata(meta: dict):
    try:
        result = guest_service.add_guest_metadata(meta)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return {"message": "Metadata added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update")
def update_guest(meta: dict, authorization: str = Header(None)):
    try:
        # Token validation
        if not authorization or authorization != "Bearer VALID_TOKEN":
            raise HTTPException(status_code=401, detail="Invalid or missing token")

        result = guest_service.update_guest(meta)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return {"message": "Guest updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{guest_id}/change_password")
async def change_password(guest_id: str,
    old_password: str = Form(None),
    secret_key: str = Form(None),
    new_password: str = Form(...),
):
    """
    Change or reset a user's password.
    Either old_password OR secret_key must be provided.
    """
    if not old_password and not secret_key:
        raise HTTPException(status_code=400, detail="Provide either old password or secret key")

    try:
        result = await guest_service.change_password(guest_id,old_password, secret_key, new_password)
        return {"message": result}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
@router.delete("/{guest_id}")
def delete_guest(guest_id: str):
    deleted = guest_service.delete_guest(guest_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Guest not found")
    return {"status": "success", "message": "Guest deleted successfully"}


@router.put("/{guest_id}/toggle")
def toggle_guest(guest_id: str):
    print(guest_id)
    result = guest_service.toggle_guest_status(guest_id)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"]) 
    
    return result

@router.post("/{guest_id}/confirm")
def confirm_guest(guest_id: str):
    print(guest_id)
    result = guest_service.confirm_guest(guest_id)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"]) 
    
    return result

@router.get("/{guest_id}")
def get_guest_details(guest_id: str):

    result = guest_service.get_guest_with_attendance(guest_id)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"]) 
    
    return result
    

