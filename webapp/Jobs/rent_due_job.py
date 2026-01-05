from datetime import date
from db.database import get_connection
from services.payment_email import PaymentEmailService

class RentDueJob:

    @staticmethod
    async def run():
        print("[JOB] Rent due insertion started")
        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                Select g.guest_id,b.sharing_type,b.bed_id,brp.monthly_rent,status from guests as a
                JOIN guest_roles AS g ON a.guest_id = g.guest_id
                Left join roles as r ON r.role_id = g.role_id
                Left join guest_beds as gb ON gb.guest_id = g.guest_id
                Left join beds as b ON b.bed_id= gb.bed_id
                Left join bed_rent_plan as brp ON brp.sharing_type = b.sharing_type
                where status <>'closed' and r.role_name ='resident'     
            """)

            rows = cur.fetchall()
            today = date.today()
            # Extract the year and month
            current_year = today.year
            current_month = today.month

            for r in rows:
                guest_id      = r[0]
                # sharing_type  = r[1]
                # bed_id        = r[2]
                # monthly_rent  = r[3]    # <-- IMPORTANT FIX
                # status        = r[4]
                calculated_rent = r[3] or 0
                guest_id = r[0]
                if calculated_rent < 0:
                    calculated_rent = 6000  # Default rent if not found
                # Insert due record
                cur.execute(f"""
                    INSERT INTO dues (guest_id, year, month, due_type_id, due_amount)
                    SELECT '{guest_id}', {current_year}, {current_month}, 1, {calculated_rent}
                    WHERE NOT EXISTS (
                        SELECT 1 FROM dues m
                        WHERE m.guest_id = '{guest_id}'
                        AND m.year = {current_year}
                        AND m.month = {current_month}
                    );
                """)
                due_id = cur.lastrowid
                        # 2️⃣ apply wallet
                apply_wallet_to_due(
                    cur,
                    guest_id,
                    due_id,
                    calculated_rent
                )
            conn.commit()

        finally:
            conn.close()



        print("[JOB] Rent due insertion completed")




def apply_wallet_to_due(cur, guest_id, due_id, due_amount):
    # 1️⃣ get wallet balance
    cur.execute("""
        SELECT COALESCE(SUM(amount), 0) AS balance
        FROM wallet_transactions
        WHERE guest_id = ?
    """, (guest_id,))
    wallet_balance = cur.fetchone()["balance"]

    if wallet_balance <= 0:
        return

    # 2️⃣ calculate adjustment
    adjust_amount = min(wallet_balance, due_amount)

    # 3️⃣ update dues
    cur.execute("""
        UPDATE dues
        SET amount_paid = amount_paid + ?,
            status = CASE
                WHEN amount_paid + ? >= due_amount THEN 'paid'
                ELSE 'partial'
            END
        WHERE id = ?
    """, (adjust_amount, adjust_amount, due_id))

    # 4️⃣ deduct from wallet
    cur.execute("""
        INSERT INTO wallet_transactions (
            guest_id, amount, reason,
            reference_id, created_at, remarks
        )
        VALUES (?, ?, 'ADVANCE_APPLIED', ?, datetime('now'), ?)
    """, (
        guest_id,
        -adjust_amount,
        due_id,
        "Advance adjusted against monthly rent"
    ))

    PaymentEmailService.send(cur,guest_id,adjust_amount)
