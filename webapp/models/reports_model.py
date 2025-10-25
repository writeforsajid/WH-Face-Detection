from pydantic import BaseModel, EmailStr
from typing import List, Optional

class ReportRequest(BaseModel):
    from_date: str
    to_date: str
    emails: List[EmailStr]

class ReportResponse(BaseModel):
    message: str
