from fastapi import APIRouter, HTTPException, Query, Header,Form
from db.database import get_connection
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from utilities.environment_variables import load_environment
import sqlite3,os,shutil
import json
from pathlib import Path
from fastapi.responses import JSONResponse


#load_environment(env_path);

load_environment("./../data/.env.webapp")
DB_PATH=os.getenv("DB_PATH")
if DB_PATH is None: DB_PATH = "./../data/WhiteHouse.db"
DB_LOCAL_PATH = Path("./../data/WhiteHouse.db")  # your existing path
ITEMS_JSON_PATH = DB_LOCAL_PATH.with_name("items.json")  # same folder, sibling file



def _require_token(auth_header: Optional[str]) -> str:
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return auth_header.split(" ", 1)[1].strip()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _validate_session(token: str) -> str:
    """Validate session token; return guest_id if valid else raise 401."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        now_iso = _iso(_now_utc())
        cur.execute(
            """
            SELECT gs.guest_id
            FROM guest_sessions gs
            WHERE gs.session_id = ?
              AND IFNULL(gs.revoked, 0) = 0
              AND gs.expires_at > ?
            """,
            (token, now_iso),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return row[0]
    finally:
        conn.close()




def get_guest_pending_rents(guest_id: str, ) -> Dict:
	"""
	Fetch guest metadata records for the window [till_date - days, till_date].

	Returns a dict with keys: status, guest_id, from_date, till_date, count, data
	"""



	conn = get_connection()
	cur = conn.cursor()

	query = ("""
            SELECT *
        FROM (
            SELECT 

                guest_id,
                created_at,
                amount AS submitted,
                NULL AS due,
                status,
                'payment' AS source
            FROM rent_payments
            WHERE guest_id = ?

            UNION ALL

            SELECT

                guest_id,
                created_at,
                NULL AS submitted,
                due_amount AS due,
                status,
                'due' AS source
            FROM dues
            WHERE guest_id = ?
        )
        ORDER BY created_at DESC;	  
""")
	

	cur.execute(query, (guest_id, guest_id))
	rows = cur.fetchall()
	# rows are sqlite3.Row because get_connection sets row_factory
	# Only include name, description, timestamp as requested
	data = [ {"created_at":datetime.fromisoformat(r["created_at"]).date().isoformat(), "submitted": r["submitted"], "due": r["due"], "status": r["status"], "source": r["source"]} for r in rows ]
	conn.close()

	return {
		"status": "success",
		"guest_id": guest_id,
		"count": len(data),
		"data": data,
	}



def get_beds_stats(guest_id: str, ) -> Dict[str, int]:
    """
    Return counts of beds using guest_beds (current assignment table):
      - total: hardcoded to 83 (as requested)
      - occupied: total number of rows in guest_beds (all assignments)
      - vacant: total - occupied

    Requires a valid bearer token.
    """

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Occupied beds: count all rows in guest_beds
        cur.execute("SELECT COUNT(*) FROM beds")
        total_beds =  int(cur.fetchone()[0] or 0)
        cur.execute("SELECT COUNT(*) FROM guest_beds")
        occupied = int(cur.fetchone()[0] or 0)
        total = total_beds
        vacant = max(total - occupied, 0)

        cur.execute(f"""SELECT 
                b.sharing_type,
                COUNT(b.bed_id) AS total_beds,
                COUNT(gb.bed_id) AS occupied_beds,
                (COUNT(b.bed_id) - COUNT(gb.bed_id)) AS vacant_beds
                FROM beds b
                LEFT JOIN guest_beds gb ON b.bed_id = gb.bed_id
                GROUP BY b.sharing_type
                ORDER BY b.sharing_type;""")
        

        rows = cur.fetchall()

        # Convert to desired dictionary format
        
        sharing_summary = {}
        for r in rows:
            stype = r["sharing_type"].lower()
            sharing_summary[f"{stype}_total"] = r["total_beds"]
            sharing_summary[stype] = r["occupied_beds"]

        sharing_summary["total"]=total;
        sharing_summary["occupied"]=occupied;
        sharing_summary["vacant"]=vacant;



        return sharing_summary


    finally:
        conn.close()






def get_my_payments(guest_id, startDate, endDate, page, pageSize):
    conn = get_connection()
    cur = conn.cursor()

    # -----------------------------
    # WHERE clause builder
    # -----------------------------
    where_clause = "guest_id = ?"
    params = [guest_id]

    if startDate:
        where_clause += " AND date(created_at) >= date(?)"
        params.append(startDate)

    if endDate:
        where_clause += " AND date(created_at) <= date(?)"
        params.append(endDate)

    # -----------------------------
    # OFFSET (Pagination)
    # -----------------------------
    offset = (page - 1) * pageSize

    # -----------------------------
    # MAIN UNION QUERY  (IMPORTANT: f-string!)
    # -----------------------------
    query = f"""
        SELECT *
        FROM (
            SELECT 
                created_at,
                amount AS submitted,
                NULL AS due,
                status,
                reference AS source,
                description AS paidby
            FROM rent_payments
            WHERE {where_clause}

            UNION ALL

            SELECT 
                created_at,
                NULL AS submitted,
                due_amount AS due,
                status,
                'due' AS source,
                 NULL AS paidby
            FROM dues
            WHERE {where_clause}
        ) AS combined
        ORDER BY created_at DESC
    """

    # -----------------------------
    # TOTAL COUNT
    # -----------------------------
    count_sql = f"SELECT COUNT(*) FROM ({query}) AS t"
    cur.execute(count_sql, params + params)   # same params twice
    total = cur.fetchone()[0]

    # -----------------------------
    # PAGINATED RESULTS
    # -----------------------------
    data_sql = query + " LIMIT ? OFFSET ?"
    cur.execute(data_sql, params + params + [pageSize, offset])
    rows = cur.fetchall()

    conn.close()

    return {
        "success": True,
        "total": total,
        "page": page,
        "pageSize": pageSize,
        "data": [
            dict(zip([
                "created_at", "submitted", "due",
                "status", "source", "paidby"
            ], r))
            for r in rows
        ]
    }

async def pay_my_rent(guest_id,paymentMode,txtAmount,currentDate,txnId,description,attachment):
    conn = get_connection()
    cur = conn.cursor()
    try:
            # ---- Validate date ----
            try:
                pay_date = datetime.strptime(currentDate, "%Y-%m-%d")
                year = pay_date.year
                month = pay_date.month

            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format")

            saved_file_path = None

            # ---- Save file (if uploaded) ----

            if attachment:
                upload_dir = "uploads/payments"

                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)

                new_filename = f"{guest_id}_{attachment.filename}"
                saved_file_path = os.path.join(upload_dir, new_filename)


                with open(saved_file_path, "wb") as buffer:
                    shutil.copyfileobj(attachment.file, buffer)

            # ---- Insert into DB (example only) ----
            # db.execute("INSERT INTO payments (...) VALUES (...)", ...)


#guest_id,paymentMode,txtAmount,currentDate,txnId,description,attachment
            payment_id = cur.execute("""
                INSERT INTO rent_payments 
                (created_by, guest_id, year, month, amount, mode, reference, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (guest_id, guest_id, year, month, txtAmount, paymentMode, txnId, description)).lastrowid

            distribute_payment(conn, guest_id, payment_id, txtAmount)

            return {
                "success": True,
                "guest_id": guest_id,
                "tran_id": txnId,
                "amount": txtAmount,
                "payment_mode": paymentMode,
                "file_path": description
            }

    except Exception as e:
        print("Payment API Error:", e)
        raise HTTPException(status_code=500, detail="Server error while processing payment")

def distribute_payment(conn, guest_id, payment_id, payment_amount):
    cursor = conn.cursor()

    # Step 1: Fetch all open/partial dues sorted oldest → newest
    cursor.execute("""
        SELECT id, due_amount, amount_paid
        FROM dues
        WHERE guest_id = ?
        AND status IN ('open','partial')
        ORDER BY year, month
    """, (guest_id,))
    
    dues = cursor.fetchall()

    remaining_payment = payment_amount

    for due in dues:
        due_id, due_amount, amount_paid = due

        if remaining_payment <= 0:
            break

        balance = due_amount - amount_paid
        if balance <= 0:
            continue

        # allocation amount for this due
        allocate = min(remaining_payment, balance)

        # INSERT PAYMENT ALLOCATION
        cursor.execute("""
            INSERT INTO rent_payment_allocations 
                (rent_payment_id, due_id, allocated_amount)
            VALUES (?, ?, ?)
        """, (payment_id, due_id, allocate))

        # UPDATE dues.amount_paid
        cursor.execute("""
            UPDATE dues
            SET amount_paid = amount_paid + ?,
                status = CASE 
                    WHEN amount_paid + ? >= due_amount THEN 'paid'
                    ELSE 'partial'
                END
            WHERE id = ?
        """, (allocate, allocate, due_id))

        remaining_payment -= allocate

    conn.commit()
    