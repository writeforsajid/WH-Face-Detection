from fastapi import APIRouter, HTTPException, Query, Header,Form
from typing import Optional, Dict
from db.database import get_connection
from services import guest_service,google_contact_service,guest_adv_sec_service
from datetime import date,datetime, timezone
from services import rentalmonth_service_models as rsm
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
def guests_stats(
    authorization: Optional[str] = Header(None),
    guest_id: str = Query(..., description="ID of the guest",), 
    ) -> Dict[str, int]:
    
    """Return guest counts by status and total."""
    token = _require_token(authorization)
    _validate_session(token)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f""" 
            SELECT COUNT(*)
            FROM attendance
            WHERE guest_id = ?
            AND date(replace(timestamp, 'T', ' ')) = date('now', 'localtime');        
        """, (guest_id,))
        
        
        attendance = int(cur.fetchone()[0] or 0)
        #---- Done -----#
        cur.execute(f""" 
        SELECT 
            (SUM(due_amount) - SUM(amount_paid)) AS balance
        FROM dues
        WHERE guest_id = ?;   
        """, (guest_id,))
        
        
        totaldue = int(cur.fetchone()[0] or 0)

        cur.execute("""
                SELECT 
                    COALESCE(
                        SUM(
                            CASE
                                WHEN wt.txn_type = 'credited' THEN wt.amount
                                WHEN wt.txn_type IN ('debited','refunded') THEN -wt.amount
                                ELSE 0
                            END
                        ), 0
                    ) AS wallet_balance
                FROM wallet_transactions wt
                JOIN wallet_accounts wa ON wa.id = wt.wallet_id
                WHERE wa.guest_id = ?
        """, (guest_id,))

        advance_balance = int(cur.fetchone()[0])

        cur.execute("""
                SELECT 
                    COALESCE(
                        SUM(
                            CASE 
                                WHEN st.txn_type = 'received' THEN st.amount
                                WHEN st.txn_type IN ('adjusted', 'refunded') THEN -st.amount
                                ELSE 0
                            END
                        ), 
                    0) AS security_balance
                FROM security_transactions st
                JOIN security_accounts sa ON sa.id = st.security_id
                WHERE sa.guest_id = ?
        """, (guest_id,))

        security_balance = int(cur.fetchone()[0])

        return {"attendance": attendance, "totaldue": totaldue,"advance_balance": advance_balance,"security_balance":security_balance }
    finally:
        conn.close()


# @router.post("/")
# def add_guest(guest: dict):
#     result = guest_service.create_guest(guest)
#     if isinstance(result, dict) and "error" in result:
#         # Handle custom error (e.g., missing video)
#         raise HTTPException(status_code=400, detail=result["error"]) 

#     return result

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

    
@router.get("/bed_numbers")
def bunch_of_beds():
    
    return guest_service.get_bunch_of_beds()


@router.get("/active")
def get_active_guests():
    """
    Fetch attendance records between given dates with pagination.
    """
 
    try:
        result = guest_service.get_active_guests()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Attendance data not found")
    return result
  


@router.get("/onload_security_advance_statement")
def get_security_statement(guest_id: str):
    try:
        advance_data = guest_adv_sec_service.get_wallet_statement(guest_id)
        security_data = guest_adv_sec_service.get_security_statement(guest_id)
        result=  {
            "advance": {
                "balance": advance_data["advance_balance"],
                "rows": advance_data["rows"]
            },
            "security": {
                "balance": security_data["security_balance"],
                "rows": security_data["rows"]
            }
        }
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.get("/activeReviewers")
def get_active_reviewers():
    """
    Fetch attendance records between given dates with pagination.
    """
 
    try:
        result = guest_service.get_active_reviewers()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Attendance data not found")
    return result
  


@router.post("/addupdatecontact")
def add_update_contact(
    guest_id: str = Form(...),
    contact_name: str = Form(...)
):
    try:
        result = google_contact_service.safe_add_or_edit_contact(guest_id, contact_name)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="User data not found")
    return result


@router.post("/harddelete")
def hard_delete_guest(
    guest_id: str = Form(...)
):
    try:
        deleted = guest_service.hard_delete_guest(guest_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Guest not found")
        return {"status": "success", "message": "Guest deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history")
def get_history_records(
    
    guest_id: str = Query(..., description="ID of the guest"),
    start_date: date = Query(..., description="Start date in YYYY-MM-DD"),
    end_date: date = Query(..., description="End date in YYYY-MM-DD"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Records per page"),
):
    """
    Fetch attendance records between given dates with pagination.
    """
 
    try:
        result = guest_service.get_history_records(guest_id, start_date, end_date, page, limit)

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


@router.get("/profile")
def get_profile_details(
    guest_id: str = Query(...)):

    result = guest_service.get_profile_details(guest_id)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"]) 
    
    return result

@router.post("/profile_update")
def update_guest(profile_data:  rsm.GuestProfileUpdate):
    try:
        print(profile_data);
        result = guest_service.update_guest(profile_data)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return {"message": "Guest updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@router.get("/validateemail")
def get_guest_details(guest_email: str):

    result = guest_service.get_guest_ifemailexist(guest_email)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"]) 
    
    
    return result




@router.post("/{guest_id}/change_password")
async def change_password(guest_id: str,
    old_password: str = Form(None),
    new_password: str = Form(...),
):
    """
    Change or reset a user's password.
    Either old_password OR secret_key must be provided.
    """
    if not old_password :
        raise HTTPException(status_code=400, detail="Provide either old password")

    try:
        result = await guest_service.change_password(guest_id,old_password,  new_password)
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
    result = guest_service.toggle_guest_status(guest_id)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"]) 
    
    return result

@router.post("/{guest_id}/confirm")
def confirm_guest(guest_id: str):
    #print(guest_id)
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
    

