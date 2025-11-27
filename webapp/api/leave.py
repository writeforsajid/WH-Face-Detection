from fastapi import APIRouter, HTTPException, Query, Header,Form
from pydantic import BaseModel
from services import leave_service


router = APIRouter()

class LeaveRequest(BaseModel):
    guest_id: str
    leave_type_id: int
    start_date: str
    end_date: str
    reason: str


@router.post("/apply")
def apply_leave(request: LeaveRequest):
    try:

        return leave_service.apply_leave_service(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))




@router.get("/search")
def get_my_leaves(
    guest_id: str = Query(...),
    startDate: str = Query(None),
    endDate: str = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1)
):
    return leave_service.get_my_leaves(
        guest_id, startDate, endDate, page, pageSize
    )

@router.get("/unapproved")
def get_unapproved_leaves(
    startDate: str = Query(None),
    endDate: str = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1)    
):
    return leave_service.get_unapproved_leaves(
         startDate, endDate,page,pageSize
    )
