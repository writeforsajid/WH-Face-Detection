from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services.metadata_service import get_guest_metadata_month

router = APIRouter()


@router.get("/metadata/guest")
def guest_metadata(
    guest_id: Optional[str] = None
):
    """
    Return guest metadata for the `days` ending at `till_date` (inclusive).
    If `till_date` is omitted, today's date is used. `days` defaults to 30.
    """
    try:
        result = get_guest_metadata_month(guest_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    



