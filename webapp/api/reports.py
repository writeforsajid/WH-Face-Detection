from fastapi import APIRouter, HTTPException,Query
from models.reports_model import ReportRequest, ReportResponse
from services import reports_service 
#import process_report_request,guest_presence_report

router = APIRouter()

@router.post("/reports", response_model=ReportResponse)
async def create_report(report: ReportRequest):
    """
    API Endpoint for generating and emailing reports.
    """
    try:
        response = reports_service.process_report_request(report)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/guest_presence")
async def guest_presence(till_date: str = Query(..., description="Format: YYYY-MM-DD")):
    """
    Generate guest presence/missing report between (till_date - 48 hrs) and till_date.
    Example: /reports/guest_presence?till_date=2025-10-02
    """
    try:
        
        response = reports_service.guest_presence_report(till_date)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/monthly")
def get_my_leaves(
    guest_id: str = Query(...),
    startDate: str = Query(None),
    endDate: str = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1)
):
    return reports_service.get_monthly_rents(
        guest_id, startDate, endDate, page, pageSize
    )