from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services.metadata_service import get_guest_metadata_month

router = APIRouter()


@router.get("/metadata/guest/{guest_id}")
def guest_metadata(
    guest_id: str,
    till_date: Optional[str] = Query(None, description="Format: YYYY-MM-DD"),
    days: Optional[int] = Query(30, description="Number of days to look back from till_date"),
):
    """
    Return guest metadata for the `days` ending at `till_date` (inclusive).
    If `till_date` is omitted, today's date is used. `days` defaults to 30.
    """
    try:
        result = get_guest_metadata_month(guest_id, till_date, days)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    



