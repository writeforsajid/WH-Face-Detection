from fastapi import APIRouter, HTTPException, Query, Header,Form
from typing import Optional, Dict
from db.database import get_connection
from services import guest_service
from datetime import datetime, timezone

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


@router.get("/stats")
def guests_stats(authorization: Optional[str] = Header(None)) -> Dict[str, int]:
    """Return guest counts by status and total."""
    token = _require_token(authorization)
    _validate_session(token)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM guests")
        total = int(cur.fetchone()[0] or 0)

        counts = {"active": 0, "inactive": 0, "closed": 0}
        cur.execute("SELECT status, COUNT(*) FROM guests GROUP BY status")
        for s, c in cur.fetchall():
            if s:
                counts[str(s).lower()] = int(c or 0)

        return {"total": total, **counts}
    finally:
        conn.close()


@router.post("/")
def add_guest(guest: dict):
    result = guest_service.create_guest(guest)
    if isinstance(result, dict) and "error" in result:
        # Handle custom error (e.g., missing video)
        raise HTTPException(status_code=400, detail=result["error"]) 

    return result

@router.get("/")
def list_guests(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by guest name"),
    status: Optional[str] = Query(
        None,
        description="Filter by status: active|inactive|closed",
        regex="^(active|inactive|closed)$",
    ),
):
    return guest_service.get_guests(page=page, limit=limit, search=search, status=status)

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
    
@router.get("/bed_numbers")
def bunch_of_beds():
    
    return guest_service.get_bunch_of_beds()

@router.get("/{guest_id}")
def get_guest_details(guest_id: str):

    result = guest_service.get_guest_with_attendance(guest_id)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"]) 
    
    return result
    

@router.get("/{guest_id}/history")
def get_guest_history(guest_id: str):
    
    result = guest_service.get_guest_history(guest_id)

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"]) 
    
    return result
  



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

    




