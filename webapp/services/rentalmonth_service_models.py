from pydantic import BaseModel
from fastapi import APIRouter
from typing import Optional
from db.database import get_connection
import sqlite3

# TODO: Models 

class PayInitialRentRequest(BaseModel):
    created_by: str
    guest_id: str
    guest_name: str

    rent_dueable: float
    security_due: float
    pay_security: float
    pay_rent: float

    trx_id: str
    pay_month_year: str
    pay_date: str
    payment_mode: str
    paid_by: str

    bedNumber: str

    # internal / workflow
    rent_payment_id: int | None = 0

    # optional flags
    approved_payment: bool = False
    activate_user: bool = False
    send_email: bool = False

    # optional UI data
    roomType: str = "-"
    roomBed: str = "-"
    roomAssignedAt: str = "-"
    bdasign: str = "-"

    admission_date: str
    billing_cycle: str
    pay_advance: float
    total_payment: float
    rent_start_date: str





class SecurityRequest(BaseModel):
    created_by: str
    guest_id: str
    pay_security: float
    pay_date: str
    payment_mode: str
    sec_remarks:str
    txn_type: str ## ('received', 'adjusted', 'refunded')
    trx_id:  Optional[str] = None



class AdvanceRequest(BaseModel):
    created_by: str
    guest_id: str
    pay_advance: float
    pay_date: str
    payment_mode: str
    sec_remarks:str
    txn_type: str ## ('received', 'adjusted', 'refunded')
    trx_id:  Optional[str] = None



# TODO: Models Profile
class GuestProfileUpdate(BaseModel):
    guest_id: str
    date_of_birth: str
    phone_number: str
    emergency_contact: str
    permanent_address: str
    pincode: str
    police_station: str
    aadhaar_number: str
    marital_status: str











