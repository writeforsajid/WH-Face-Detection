from Designs.Chain_of_Responsibility import Task 
from services.google_contact_service import safe_add_or_edit_contact
from services.Biz_Log import PaymentActionService as pas 
from datetime import datetime
from fastapi import  HTTPException
from db.database import get_connection
from typing import Optional
import sqlite3
from services.rentalmonth_service_models import SecurityRequest

# TODO:  Initate Classes Chain of Responsibilities

class ParseMonthTask(Task):
    def validate(self, ctx):
        try:
            year, month = map(int, ctx.get("pay_month_year").split("-"))
            ctx.set("year", year)
            ctx.set("month", month)
            return True
        except:
            ctx.fail("Invalid pay_month_year format (YYYY-MM)")
            return False

    def process(self, ctx): pass

class ValidatePaymentModeTask(Task):
    def validate(self, ctx):
        return ctx.get("payment_mode") in ("UPI", "CASH", "IMPS", "DD")
           

    def process(self, ctx): pass

class ActivateGuestTask(Task):
    def validate(self, ctx): 
        return bool(ctx.get("activate_user"))

    def process(self, ctx):
        ctx.get("cur").execute("""
            UPDATE guests SET status='_blank' WHERE guest_id=?
        """, (ctx.get("guest_id"),))

class RentDueTask(Task):
    def validate(self, ctx):
        return ctx.get("rent_dueable") and float(ctx.get("rent_dueable")) > 0

    def get_due_type_id(self, cur, code):
        cur.execute("SELECT id FROM due_types WHERE code=?", (code,))
        row = cur.fetchone()
        if not row:
            
            return None
        return row["id"]

    def process(self, ctx):
        cur = ctx.get("cur")
        guest_id = ctx.get("guest_id")
        year, month = ctx.get("year"), ctx.get("month")
        amount = float(ctx.get("rent_dueable"))

        due_type_id = self.get_due_type_id(cur, "RENT")
        if not due_type_id:
            return

        cur.execute("""
            SELECT id, due_amount FROM dues
            WHERE guest_id=? AND due_type_id=? AND year=? AND month=?
        """, (guest_id, due_type_id, year, month))

        row = cur.fetchone()
        if row:
            cur.execute("""
                UPDATE dues SET due_amount=?, created_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (row["due_amount"] + amount, row["id"]))
        else:
            cur.execute("""
                INSERT INTO dues
                (guest_id,due_type_id,year,month,due_amount,amount_paid,status,created_at)
                VALUES (?,?,?,?,?,0,'open',CURRENT_TIMESTAMP)
            """, (guest_id, due_type_id, year, month, amount))



class AdvanceDueTask(Task):
    def validate(self, ctx):
        return ctx.get("pay_advance") and float(ctx.get("pay_advance")) > 0


    def process(self, ctx):
        cur = ctx.get("cur")
        guest_id = ctx.get("guest_id")
        pay_advance = float(ctx.get("pay_advance"))
        rent_payment_id=0

        txn_type=ctx.get("txn_type") 
        if not txn_type: txn_type = 'credited'
        pay_date = ctx.get("pay_date")
        if not pay_date: pay_date = datetime.now() 
        sec_remarks = ctx.get("sec_remarks")
        if not sec_remarks: sec_remarks = 'Advance received'
        trx_id = ctx.get("trx_id")
        if not trx_id: trx_id = 0


        # ============================
        # 3️⃣ ADVANCE PAYMENT (WALLET)
        # ============================

        wallet_id = self._get_or_create_wallet(cur, guest_id)

        cur.execute("""
            INSERT INTO wallet_transactions (
                wallet_id,
                amount,
                txn_type,
                reference_id,
                created_at,
                remarks
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            wallet_id,
            pay_advance,          # POSITIVE amount
            txn_type,
            rent_payment_id,
            pay_date,
            sec_remarks
        ))


    def _get_or_create_wallet(self,cur, guest_id):
        cur.execute("""
            SELECT id
            FROM wallet_accounts
            WHERE guest_id = ?
        """, (guest_id,))

        row = cur.fetchone()
        if row:
            return row["id"]

        cur.execute("""
            INSERT INTO wallet_accounts (guest_id, created_on)
            VALUES (?, datetime('now'))
        """, (guest_id,))

        return cur.lastrowid



class SecurityDueTask(Task):
    def validate(self, ctx):
        return ctx.get("pay_security") and float(ctx.get("pay_security")) > 0




    
    def process(self, ctx):

        cur = ctx.get("cur")
        guest_id = ctx.get("guest_id")
        pay_security = float(ctx.get("pay_security"))
        rent_payment_id=int(ctx.get("rent_payment_id"))
        payment_mode=ctx.get("payment_mode")
        

        txn_type=ctx.get("txn_type") 
        if not txn_type: txn_type = 'received'
        pay_date = ctx.get("pay_date")
        if not pay_date: pay_date = datetime.now() 
        sec_remarks = ctx.get("sec_remarks")
        if not sec_remarks: sec_remarks = 'Collected with rent payment'
        trx_id = ctx.get("trx_id")
        if not trx_id: trx_id = 0

        
        
        
        # Ensure security account exists
        sec = cur.execute("""
            SELECT id FROM security_accounts
            WHERE guest_id = ?
        """, (guest_id,)).fetchone()

        if not sec:
            cur.execute("""
                INSERT INTO security_accounts (guest_id, created_on)
                VALUES (?, ?)
            """, (guest_id,pay_date))
            security_id = cur.lastrowid
        else:
            security_id = sec["id"]

        cur.execute("""
            INSERT INTO security_transactions
            (security_id, amount, txn_type, payment_mode, reference_id, created_at, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            security_id,
            pay_security,
            txn_type,
            payment_mode,
            rent_payment_id,
            pay_date,
            sec_remarks
        ))
        



class SecurityDueTaskPartTwo(Task):

    def validate(self, ctx):
       return ctx.get("pay_security") and float(ctx.get("pay_security")) > 0

    def process(self, ctx):
        cur = ctx.get("cur")
        guest_id = ctx.get("guest_id")
        pay_security = float(ctx.get("pay_security"))
        rent_payment_id=0
        payment_mode=ctx.get("payment_mode")
        

        txn_type=ctx.get("txn_type") 
        if not txn_type: txn_type = 'received'
        pay_date = ctx.get("pay_date")
        if not pay_date: pay_date = datetime.now() 
        sec_remarks = ctx.get("sec_remarks")
        if not sec_remarks: sec_remarks = 'Collected with rent payment'
        trx_id = ctx.get("trx_id")
        if not trx_id: trx_id = 0

        
        
        
        # Ensure security account exists
        sec = cur.execute("""
            SELECT id FROM security_accounts
            WHERE guest_id = ?
        """, (guest_id,)).fetchone()

        if not sec:
            cur.execute("""
                INSERT INTO security_accounts (guest_id, created_on)
                VALUES (?, ?)
            """, (guest_id,pay_date))
            security_id = cur.lastrowid
        else:
            security_id = sec["id"]

        cur.execute("""
            INSERT INTO security_transactions
            (security_id, amount, txn_type, payment_mode, reference_id, created_at, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            security_id,
            pay_security,
            txn_type,
            payment_mode,
            rent_payment_id,
            pay_date,
            sec_remarks
        ))




class AdvanceDueTaskPartTwo(Task):
    def validate(self, ctx):
        return ctx.get("pay_advance") and float(ctx.get("pay_advance")) > 0

    def _get_or_create_wallet(self,cur, guest_id):
        cur.execute("""
            SELECT id
            FROM wallet_accounts
            WHERE guest_id = ?
        """, (guest_id,))

        row = cur.fetchone()
        if row:
            return row["id"]

        cur.execute("""
            INSERT INTO wallet_accounts (guest_id, created_on)
            VALUES (?, datetime('now'))
        """, (guest_id,))

        return cur.lastrowid


    def process(self, ctx):
        cur = ctx.get("cur")
        guest_id = ctx.get("guest_id")
        pay_advance = float(ctx.get("pay_advance"))
        rent_payment_id=0

        txn_type=ctx.get("txn_type") 
        if not txn_type: txn_type = 'credited'
        pay_date = ctx.get("pay_date")
        if not pay_date: pay_date = datetime.now() 
        sec_remarks = ctx.get("sec_remarks")
        if not sec_remarks: sec_remarks = 'Advance received'
        trx_id = ctx.get("trx_id")
        if not trx_id: trx_id = 0


        # ============================
        # 3️⃣ ADVANCE PAYMENT (WALLET)
        # ============================

        wallet_id = self._get_or_create_wallet(cur, guest_id)

        cur.execute("""
            INSERT INTO wallet_transactions (
                wallet_id,
                amount,
                txn_type,
                reference_id,
                created_at,
                remarks
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            wallet_id,
            pay_advance,          # POSITIVE amount
            txn_type,
            rent_payment_id,
            pay_date,
            sec_remarks
        ))


class RentPaymentTask(Task):
    def validate(self, ctx):
        return ctx.get("pay_rent") and float(ctx.get("pay_rent")) > 0

    def process(self, ctx):
        ctx.get("cur").execute("""
            INSERT INTO rent_payments
            (created_by,guest_id,year,month,amount,mode,reference,description,status,created_at)
            VALUES (?,?,?,?,?,?,?,?, 'submitted', datetime('now'))
        """, (
            ctx.get("created_by"),
            ctx.get("guest_id"),
            ctx.get("year"),
            ctx.get("month"),
            float(ctx.get("pay_rent")),
            ctx.get("payment_mode"),
            ctx.get("trx_id"),
            ctx.get("paid_by")
        ))

        rent_payment_id = ctx.get("cur").lastrowid   # 🔥 KEY LINE
        ctx.set("rent_payment_id", rent_payment_id)



class AssignBed(Task):
    def validate(self, ctx):
        return  bool(ctx.get("bedNumber")) and ctx.get("bedNumber").count("/") == 2

    def process(self, ctx):
        cur = ctx.get("cur")
        guest_id = ctx.get("guest_id")
        bedNumber= ctx.get("bedNumber")
        roomAssignedAt= ctx.get("roomAssignedAt")
       # Check if bed exists
        cur.execute("SELECT bed_id FROM beds WHERE bed_id = ?", (bedNumber,))
        bed_row = cur.fetchone()
        if not bed_row:
            return
        
        bed_id = bed_row[0]
        
        # Check if guest exists
        cur.execute("SELECT guest_id, name FROM guests WHERE guest_id = ?", (guest_id,))
        guest_row = cur.fetchone()
        if not guest_row:
            return
        
        # Check if guest is already assigned to any bed
        cur.execute("SELECT bed_id FROM guest_beds WHERE guest_id = ?", (guest_id,))
        existing_assignment = cur.fetchone()
        if existing_assignment:
                return
        
        # Check if bed already has a guest assigned
        cur.execute("SELECT guest_id FROM guest_beds WHERE bed_id = ?", (bed_id,))
        existing_guest = cur.fetchone()
        if existing_guest:
            return
            
        try:
            assign_date = datetime.strptime(roomAssignedAt, "%Y-%m-%d").strftime("%Y-%m-%d")
        except Exception:
            assign_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Insert assignment into guest_beds

        cur.execute(
            "INSERT INTO guest_beds (guest_id, bed_id, assign_date) VALUES (?, ?, ?)",
            (guest_id, bed_id, assign_date)
        )
        cur.execute(
            """
            INSERT INTO guest_metadata (guest_id, name, description, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (guest_id, 'registered', bed_id + ' is registered', assign_date)
        )
        cur.execute(
            """
            INSERT INTO guest_metadata (guest_id, name, description, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (guest_id, 'bed assigned', bed_id + ' is assigned', assign_date)
        )
               
        # Update guest status to 'active' since they're being assigned to a bed
        cur.execute(
            "UPDATE guests SET status = 'active' WHERE guest_id = ?",
            (guest_id,)
        )
        




class ApprovePayment(Task):
    
    def validate(self, ctx):
        return  bool(ctx.get("approved_payment")) and ctx.get("rent_dueable") and float(ctx.get("rent_dueable")) > 0


    def process(self, ctx):
        cur = ctx.get("cur")
        guest_id = ctx.get("guest_id")
        rent_payment_id= ctx.get("rent_payment_id")
        approver= ctx.get("created_by")
        pas.PaymentActionService.approve(cur,rent_payment_id,approver)


class AddEditPhoneNoToContact(Task):
    
    def validate(self, ctx):
       return ctx.get("guest_id") and ctx.get("guest_name")  


    def process(self, ctx):
        cur = ctx.get("cur")
        guest_id = ctx.get("guest_id")
        guest_name = ctx.get("guest_name")
        bedNumber= ctx.get("bedNumber")
        
        pay_security= ctx.get("pay_security")
        pay_rent= ctx.get("pay_rent")
        total_payment= ctx.get("total_payment")
        prefix = "AV. "
        if (total_payment< pay_security +pay_rent): prefix="AV.D. "
        guest_name =prefix  + guest_name + " "+ bedNumber
        safe_add_or_edit_contact(guest_id, guest_name)






