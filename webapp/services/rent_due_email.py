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
            email_enabled=True
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

    'active' AS state,

    balances.id,
    balances.balance AS due_amount,

    /* ✅ Security actually paid & remaining */
    COALESCE(sec.security_balance, 0) AS security_amount

FROM guests g

/* 🔴 Only guests with outstanding dues */
JOIN (
    SELECT 
        guest_id,
        MIN(id) AS id,
        SUM(due_amount - amount_paid) AS balance
    FROM dues
    GROUP BY guest_id
    HAVING balance > 0
) balances 
    ON balances.guest_id = g.guest_id


/* 🛏 Latest assigned bed */
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
) b 
    ON g.guest_id = b.guest_id


LEFT JOIN beds bed 
    ON bed.bed_id = b.bed_id


/* 🔐 Security balance from transactions */
LEFT JOIN (
    SELECT
        sa.guest_id,
        SUM(
            CASE
                WHEN st.txn_type = 'received' THEN st.amount
                WHEN st.txn_type IN ('adjusted','refunded') THEN -st.amount
                ELSE 0
            END
        ) AS security_balance
    FROM security_accounts sa
    LEFT JOIN security_transactions st
        ON st.security_id = sa.id
    GROUP BY sa.guest_id
) sec
    ON sec.guest_id = g.guest_id


WHERE g.status <> 'closed'
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
