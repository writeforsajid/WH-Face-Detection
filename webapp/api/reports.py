from fastapi import APIRouter, HTTPException
from models.reports_model import ReportRequest, ReportResponse
from services.reports_service import process_report_request

router = APIRouter()

@router.post("/reports", response_model=ReportResponse)
async def create_report(report: ReportRequest):
    """
    API Endpoint for generating and emailing reports.
    """
    try:
        response = process_report_request(report)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
