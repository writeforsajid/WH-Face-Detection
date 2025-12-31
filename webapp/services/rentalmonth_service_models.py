from pydantic import BaseModel
from fastapi import APIRouter
# class PayInitialRentRequest(BaseModel):
#     created_by: str
#     guest_id: str
#     rent_dueable: float
#     security_due: float
#     pay_security: float
#     pay_rent: float
#     trx_id: str
#     pay_month_year: str
#     pay_date: str
#     payment_mode: str
#     paid_by: str
#     bedNumber: str
#     rent_payment_id: int | None = 0

#     # Optional extra fields (sent from JS)
#     approved_payment: bool | None = False
#     activate_user: bool | None = False
#     send_email: bool | None = False
#     roomType: str | None = "-"
#     roomBed: str | None = "-"
#     roomAssignedAt: str | None = "-"
#     bdasign: str | None = "-"




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
