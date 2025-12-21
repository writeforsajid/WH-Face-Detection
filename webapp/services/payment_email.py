from utilities.email_service import send_email


class PaymentEmailService:

    @staticmethod
    async def send(cur, guest_id, amount):
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
