from fastapi import APIRouter, HTTPException,Query,Header
from models.reports_model import ReportRequest, ReportResponse
from services import sys_service,log_service
from typing import Optional, List, Dict
from datetime import datetime, timezone
#from auth import _require_token, _validate_session
#router = APIRouter(prefix="/auth", tags=["Auth"])
router = APIRouter()



def _require_token(auth_header: Optional[str]) -> str:
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return auth_header.split(" ", 1)[1].strip()

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


# def _validate_session(token: str) -> str:
#     """Validate session token; return guest_id if valid else raise 401."""
#     conn = get_connection()
#     cur = conn.cursor()
#     try:
#         now_iso = _iso(_now_utc())
#         cur.execute(
#             """
#             SELECT gs.guest_id
#             FROM guest_sessions gs
#             WHERE gs.session_id = ?
#               AND IFNULL(gs.revoked, 0) = 0
#               AND gs.expires_at > ?
#             """,
#             (token, now_iso),
#         )
#         row = cur.fetchone()
#         if not row:
#             raise HTTPException(status_code=401, detail="Invalid or expired token")
#         return row[0]
#     finally:
#         conn.close()




@router.get("/appconfig")
def get_appconfig(name: str = Query(..., description="AppConfig name, e.g. LOG_ITEMS")):
    data = sys_service.get_appconfig_by_name(name)
    if not data:
        raise HTTPException(status_code=404, detail=f"AppConfig '{name}' not found")
    return data



# @router.get("/search")
# def search_guest_metadata(
#     #authorization: Optional[str] = Header(None),
#     start_date: str = Query(..., description="YYYY-MM-DD"),
#     end_date: str = Query(..., description="YYYY-MM-DD"),
#     name: Optional[str] = None,
#     text: Optional[str] = None
# ) -> List[Dict]:

#     # token = _require_token(authorization)
#     # _validate_session(token)
#     result = log_service.search(start_date,end_date,name,text)

#     if isinstance(result, dict) and "error" in result:
#         raise HTTPException(status_code=400, detail=result["error"])

#     return result

@router.get("/search")
def search_guest_metadata(
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    guest_id: Optional[str] = None,
    name: Optional[str] = None,
    text: Optional[str] = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1)
):
    result = log_service.search(startDate, endDate, guest_id, name, text, page, pageSize)

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result