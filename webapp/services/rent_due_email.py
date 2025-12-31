from datetime import date
from db.database import get_connection
from utilities.email_service import send_email
import asyncio
from services.log_service import add_guest_metadata
from datetime import datetime

class RentDueEmailService:

    @staticmethod
    async def send():
        print("[EMAIL] Rent due email started")

        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                "SELECT description FROM appconfig WHERE name = ?",
                ("EMAIL_NOTIFICATION",)
            )
            row = cur.fetchone()
            conn.close()
            email_enabled==True
            if row:
                email_enabled = row and row[0].lower() == "on"

            cur.execute("""
            SELECT 
                g.guest_id,
                g.name,
                g.email,
                b.bed_id AS bed_number,
                b.bed_id AS title,
                bed.sharing_type,
                'active' as state,
                balances.id,
                balances.balance AS due_amount,
                COALESCE(sec_paid.security_paid, 0) AS security_amount

            FROM guests g

            JOIN (
                SELECT 
                    guest_id,
                    MIN(id) AS id,   -- Single ID reference
                    SUM(due_amount - amount_paid) AS balance
                FROM dues
                GROUP BY guest_id
                HAVING balance > 0
            ) balances ON balances.guest_id = g.guest_id


            LEFT JOIN (
                SELECT 
                    gb.guest_id,
                    gb.bed_id
                FROM guest_beds gb
                JOIN (
                    SELECT guest_id, MAX(assign_date) AS max_date
                    FROM guest_beds
                    GROUP BY guest_id
                ) last_bed
                    ON gb.guest_id = last_bed.guest_id
                AND gb.assign_date = last_bed.max_date
            ) b ON g.guest_id = b.guest_id


            LEFT JOIN beds bed 
                ON bed.bed_id = b.bed_id


            LEFT JOIN (
                SELECT 
                    d.guest_id,
                    SUM(d.due_amount) AS security_expected
                FROM dues d
                JOIN due_types dt ON d.due_type_id = dt.id
                WHERE dt.code = 'SECURITY'
                GROUP BY d.guest_id
            ) sec_due ON g.guest_id = sec_due.guest_id


            LEFT JOIN (
                SELECT 
                    guest_id,
                    SUM(amount - refunded_amount) AS security_paid
                FROM security_deposits
                GROUP BY guest_id
            ) sec_paid ON g.guest_id = sec_paid.guest_id
            where g.status <>'closed'
            ORDER BY b.bed_id ASC;



            """)

            today = date.today()

            for guest_id, name, email, due_amount in cur.fetchall():
                if not email:
                    continue

                if email_enabled and email:
                    await send_email(
                        to=[email],
                        subject="Test Email: Please ignore", ####f"Rent Due till– {today.strftime('%B %Y')}",
                        template_name="rent_due.html",
                        template_data={
                            "name": name,
                            "amount": due_amount,
                            "month": today.strftime('%B %Y'),
                            "company_name": "White House residence"
                        },
                        guest_id=guest_id
                    )
                meta = {}                       # declare
                meta["guest_id"] = guest_id
                meta["name"] = "email_rent_due"
                meta["description"] = "rent due for the month of " +today.strftime('%B %Y')
                meta["timestamp"] =  datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                add_guest_metadata(meta)
                await asyncio.sleep(0.5)

        finally:
            conn.close()

        print("[EMAIL] Rent due email completed")
