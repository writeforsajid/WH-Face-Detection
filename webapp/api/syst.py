from fastapi import APIRouter, HTTPException,Query
from models.reports_model import ReportRequest, ReportResponse
from services import sys_service
#router = APIRouter(prefix="/auth", tags=["Auth"])
router = APIRouter()


@router.get("/appconfig")
def get_appconfig(name: str = Query(..., description="AppConfig name, e.g. LOG_ITEMS")):
    data = sys_service.get_appconfig_by_name(name)
    if not data:
        raise HTTPException(status_code=404, detail=f"AppConfig '{name}' not found")
    return data


