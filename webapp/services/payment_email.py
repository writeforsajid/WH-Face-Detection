from utilities.email_service import send_email
from services.log_service import add_guest_metadata
from datetime import datetime

class PaymentEmailService:

    @staticmethod
    async def send(cur, guest_id, amount):
        cur.execute(
            "SELECT description FROM appconfig WHERE name = ?",
            ("EMAIL_NOTIFICATION",)
        )
        row = cur.fetchone()
        email_enabled=True
        if row:
            email_enabled = row and row[0].lower() == "on"

        cur.execute("""
            SELECT name, email FROM guests WHERE guest_id=?
        """, (guest_id,))
        guest = cur.fetchone()

        cur.execute("""
            SELECT COALESCE(SUM(due_amount - amount_paid),0)
            FROM dues WHERE guest_id=?
        """, (guest_id,))
        remaining_due = cur.fetchone()[0]

        if guest and guest[1]:
            if email_enabled:
                await send_email(
                    to=[guest[1]],
                    subject="Payment Received",
                    template_name="payment_received.html",
                    template_data={
                        "name": guest[0],
                        "paid_amount": amount,
                        "remaining_due": remaining_due,
                        "company_name": "WH PG"
                    },
                    guest_id=guest_id
                )
            meta = {}                       # declare
            meta["guest_id"] = guest_id
            meta["name"] = "email_payment_received"
            meta["description"] = "payment_received "
            meta["timestamp"] =  datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            add_guest_metadata(meta)
