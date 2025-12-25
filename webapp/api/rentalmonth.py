from fastapi import APIRouter, File, HTTPException, Query, Header,Form, UploadFile
from pydantic import BaseModel
from services import rentalmonth_service,dash_rental_service,rentalmonth_service_models
from datetime import datetime, timezone
from typing import List, Dict, Optional,Any

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


@router.get("/tillmonthrent")
def get_rent_tillmonth(
    year: int = Query(1, ge=1),
    month: int = Query(10, ge=1)
):
    return rentalmonth_service.get_rent_tillmonth(
        year, month
    )

@router.get("/guestswithdues")
def get_guests_with_dues(
):
    return rentalmonth_service.get_guests_with_dues()




@router.get("/records")
def get_attendance_records(
    guest_id: str = Query(..., description="ID of the guest"),
    start_date: str = Query(..., description="Start date in YYYY-MM-DD"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD"),
    page: int = Query(1, description="Page number"),
    pageSize: int = Query(50, description="Records per page"),
):
    """
    Fetch attendance records between given dates with pagination.
    """

    try:
        start_date = datetime.fromisoformat(start_date).date()
        end_date = datetime.fromisoformat(end_date).date()
        result = rentalmonth_service.fetch_attendance(guest_id,  start_date, end_date, page, pageSize)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Attendance data not found")
    return result


@router.get("/dash-rent")
def guest_dash_rent(guest_id: str = Query(..., description="ID of the guest",),):
    """
    Fetch attendance records between given dates with pagination.
    """
    try:

        result = dash_rental_service.get_guest_pending_rents(guest_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Attendance data not found")
    return result    


@router.get("/stats")
def get_beds_stats(guest_id: str = Query(..., description="ID of the guest",),
                   authorization: Optional[str] = Header(None),
                   ) -> Dict[str, int]:
    """
    Return counts of beds using guest_beds (current assignment table):
      - total: hardcoded to 83 (as requested)
      - occupied: total number of rows in guest_beds (all assignments)
      - vacant: total - occupied

    Requires a valid bearer token.
    """
    return dash_rental_service.get_beds_stats() 


@router.get("/search")
def get_my_payments(
    guest_id: str = Query(...),
    startDate: str = Query(None),
    endDate: str = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1)
):
    return dash_rental_service.get_my_payments(
        guest_id, startDate, endDate, page, pageSize
    )


@router.post("/pay")
async def pay_my_rent(
    guest_id: str = Form(...),
    paymentMode: str = Form(...),
    txtAmount: float = Form(...),
    currentDate: str = Form(...),
    txnId: str = Form(...),
    description: str = Form(...),
    attachment: UploadFile = File(None),
):
    """
    Fetch attendance records between given dates with pagination.
    """
    try:
        result = await dash_rental_service.pay_my_rent(
        guest_id,paymentMode,txtAmount,currentDate,txnId,description,attachment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Attendance data not found")
    return result

@router.get("/get_unprocessed_payments")
def get_unprocessed_payments(
    authorization: Optional[str] = Header(None),
    search: Optional[str] = None,
    status: Optional[str] = Query(None, regex="^(active|inactive|closed)$"),
    sharing_type: Optional[str] = Query(None, regex="^(brass|silver|golden)$"),
) -> List[Dict]:
    return rentalmonth_service.get_unprocessed_payments(authorization, search, status, sharing_type)


@router.get("/get_processed_payments")
def get_processed_payments(
    authorization: Optional[str] = Header(None),
    search: Optional[str] = None,
    status: Optional[str] = Query(None, regex="^(active|inactive|closed)$"),
    sharing_type: Optional[str] = Query(None, regex="^(brass|silver|golden)$"),
) -> List[Dict]:
    return rentalmonth_service.get_processed_payments(authorization, search, status, sharing_type)


@router.get("/approve")
def approve_rent_payment(
    rent_payment_id: str = Query(...),
    approver: str = Query(None),
    comment: str = Query(None),
) :
    return rentalmonth_service.approve_rent_payment( rent_payment_id, approver, comment)



@router.get("/reject")
def reject_rent_payment( 
    rent_payment_id: str = Query(...),
    approver: str = Query(None),
    comment: str = Query(None),
) :
    return rentalmonth_service.reject_rent_payment( rent_payment_id, approver, comment)



@router.get("/cancel")
def cancel_rent_payment( 
    rent_payment_id: str = Query(...),
    approver: str = Query(None),
    comment: str = Query(None),
) :
    return rentalmonth_service.cancel_rent_payment( rent_payment_id, approver, comment)



@router.get("/forward")
def forward_rent_payment( 
    rent_payment_id: str = Query(...),
    from_user: str = Query(...),
    to_user: str = Query(...),
    comment: str = None
) :
    return rentalmonth_service.forward_rent_payment( rent_payment_id, from_user,to_user, comment)



@router.get("/onloadaction")
def get_onloadaction( 
    guest_id: str = Query(...),
) ->  Dict[str, Any]:
    
    return rentalmonth_service.get_onloadaction( guest_id)


@router.post("/payrent")
def pay_rent(
    created_by:str = Form(...),
    guest_id:str = Form(...),
    pay_rent: float = Form(...),
    trx_id: str = Form(...),
    pay_month_year: str = Form(...),        
    pay_date: str = Form(...),          # YYYY-MM or YYYY-MM-DD
    payment_mode: str = Form(...),
    paid_by: str = Form(...)
):
        return rentalmonth_service.pay_rent(created_by, guest_id,pay_rent,trx_id,pay_month_year,pay_date,payment_mode,paid_by)


@router.post("/adddues")
def add_dues(
    guest_id:str = Form(...),
    dues_amount: float = Form(...),
    dues_type: str = Form(...),
    due_month_year: str = Form(...),          # YYYY-MM or YYYY-MM-DD
    due_date: str = Form(...)
):
        return rentalmonth_service.add_dues( guest_id,dues_amount,dues_type,due_month_year,due_date)



@router.post("/payInitialrent")
def pay_initial_rent(
payload: rentalmonth_service_models.PayInitialRentRequest
):
        
        return rentalmonth_service.pay_initial_rent(payload)
        #return rentalmonth_service.pay_initial_rent(created_by, guest_id,rent_dueable,pay_security,pay_rent,trx_id,pay_month_year,pay_date,payment_mode,paid_by)



@router.post("/clear_moveout")
def clear_moveout_rent(
    guest_id:str = Form(...),
    refund_amount: float = Form(...),
    trx_id: str = Form(...),
    pay_month_year: str = Form(...),        
    pay_date: str = Form(...),          # YYYY-MM or YYYY-MM-DD
    payment_mode: str = Form(...),
    paid_by: str = Form(...)
):
        
					#data.security_paid   = section.find(".security-paid").val();
					#data.refund_amount   = section.find(".rent-paid").val();

        
        return rentalmonth_service.clear_moveout_rent( guest_id,refund_amount,trx_id,pay_month_year,pay_date,payment_mode,paid_by)


@router.post("/update_amount")
def update_payment_amount(
    rent_payment_id: int = Form(...),
    amount: float = Form(...),
):
        return rentalmonth_service.update_payment_amount( rent_payment_id,amount)


def parse_date(value: str):
    value = value.strip()  # ✅ remove extra spaces

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Invalid date format: {value}")

@router.get("/list_guest_dues")
def list_guest_dues(
    guest_id: str = Query(...),
    startDate: str = Query(None),
    endDate: str = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(100, ge=1)
):
   
    """
    Fetch attendance records between given dates with pagination.
    """

    try:
        # start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S").date()
        # end_date   = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S").date()
        start_date = parse_date(startDate)
        end_date   = parse_date(endDate)
        # start_date = datetime.fromisoformat(start_date).date()
        # end_date = datetime.fromisoformat(end_date).date()
        return rentalmonth_service.list_guest_dues(
        guest_id, start_date, end_date, page, pageSize
    )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Attendance data not found")
    return result


   
   
@router.post("/update_due_amount")
def update_due_amount(
    id: int = Form(...),
    due_amount: float = Form(...),
):
        return rentalmonth_service.update_due_amount( id,due_amount)   


@router.get("/dues-of-guest")
def duesofguest(
    guest_id: str = Query(...),
    year: int = Query(...),
    month: int = Query(...),
    due_type_id: Optional[int] = Query(None),
):
        return rentalmonth_service.duesofguest( guest_id,year,month,due_type_id) 






