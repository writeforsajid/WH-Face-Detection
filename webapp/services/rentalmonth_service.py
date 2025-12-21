from db.database import get_connection
from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional, List, Dict, Any
from db.database import get_connection
from datetime import datetime, timezone

from typing import List, Dict, Optional
from utilities.environment_variables import load_environment
import os, json
from pathlib import Path
from services.rentalmonth_guest_due_settlement import GuestDueSettlement
#load_environment(env_path);

load_environment("./../data/.env.webapp")
DB_PATH=os.getenv("DB_PATH")
if DB_PATH is None: DB_PATH = "./../data/WhiteHouse.db"
DB_LOCAL_PATH = Path("./../data/WhiteHouse.db")  # your existing path
ITEMS_JSON_PATH = DB_LOCAL_PATH.with_name("items.json")  # same folder, sibling file






router = APIRouter()


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









def get_rent_tillmonth(year: int, month: int) -> Dict:
    """
    Fetch guest metadata records for the window [till_date - days, till_date].
    Returns a dict with keys: status, guest_id, from_date, till_date, count, data
    """
    try:
        conn = get_connection()
        cur = conn.cursor()




    # 2) Fetch paginated list
        cur.execute(f"""
            SELECT 
                g.guest_id,
                g.name,
                b.bed_id AS bed_number,
                b.bed_id AS title,
                bed.sharing_type,
                'active' as state,
                balances.id,
                balances.balance AS amount,
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

            ORDER BY b.bed_id ASC;
        """)
        rows = cur.fetchall()
        result = []
        for r in rows:

            result.append({
                "id": r["id"],
                "title": r["title"],
                "name": r["name"],
                "bed_number": r["bed_number"],
                "amount": r["amount"],
                "state": r["state"],
                "sharing_type": r["sharing_type"],
                "security_amount": r["security_amount"]
            })


        # with open(ITEMS_JSON_PATH, "r", encoding="utf-8") as f:
        #     data = json.load(f)
        return result
    except FileNotFoundError:
        return {"error": "items.json not found"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format"}
    

def get_guests_with_dues() -> Dict:
    """
    Fetch guests with dues.
    Returns a dict with keys: status, guest_id, from_date, till_date, count, data
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

    # 2) Fetch paginated list
        cur.execute(f"""
        SELECT 
            g.guest_id,
            g.name,
            b.bed_id AS current_bed,
            balances.balance
        FROM guests g

        JOIN (
            SELECT 
                guest_id,
                SUM(due_amount - amount_paid) AS balance
            FROM dues
            GROUP BY guest_id
            HAVING balance > 0
        ) AS balances ON balances.guest_id = g.guest_id

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

        ORDER BY b.bed_id ASC;
        """)
        rows = cur.fetchall()
        result = []
        for r in rows:
            if r["current_bed"]:
                category = "Floor " + r["current_bed"][:1]
            else:
                category = ""
            result.append({
                "label": f'{r["name"]}' + (f' (Bed: {r["current_bed"]})' if r["current_bed"] else ''),
                "category": category
            })


        # with open(ITEMS_JSON_PATH, "r", encoding="utf-8") as f:
        #     data = json.load(f)
        return result
    except FileNotFoundError:
        return {"error": "items.json not found"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format"} 
    

def fetch_attendance(guest_id, start_date, end_date, page, limit):
    offset = (page - 1) * limit
    conn = get_connection()
    cur = conn.cursor()
    
    # --- Base query parts ---
    base_query = """
        FROM dues AS a
        JOIN guests AS g ON a.guest_id = g.guest_id
        LEFT JOIN due_types AS dt ON a.due_type_id = dt.id
        WHERE DATE(a.created_at) BETWEEN ? AND ?
    """

    params = [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]

    # Optional guest filter
    if guest_id != "all":
        base_query += " AND a.guest_id = ?"
        params.append(guest_id)



    # --- Fetch paginated records ---
    cur.execute(f"""
        SELECT 
            a.id,
            g.name as guest_name,
            dt.name as due_type_name,
            a.year,
            a.month,
            a.due_amount,
            a.amount_paid,
            a.status,
            a.created_at
        {base_query}
        ORDER BY a.created_at DESC
        LIMIT ? OFFSET ?
    """, [*params, limit, offset])
    records = cur.fetchall()
    data = []
    for row in records:
        timestamp_str = row["created_at"]
        fulltime=datetime.fromisoformat(timestamp_str)

        data.append({
            "id": row["id"],
            "guest_name": row["guest_name"],
            "due_type_name": row["due_type_name"],            
            "year": row["year"],
            "month": row["month"],
            "due_amount": row["due_amount"],
            "amount_paid": row["amount_paid"],
            "status": row["status"],
            "date":  row["created_at"],
        })

    # --- Total count ---
    cur.execute(f"SELECT COUNT(*) AS total {base_query}", params)
    total = cur.fetchone()["total"]
    conn.close()
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": data
    }

def get_unprocessed_payments(    
    authorization: Optional[str] = Header(None),
    search: Optional[str] = None,
    status: Optional[str] = Query(None, regex="^(active|inactive|closed)$"),
    sharing_type: Optional[str] = Query(None, regex="^(brass|silver|golden)$"),
) -> List[Dict]:
    """
    Fetch guest metadata records for the window [till_date - days, till_date].
    Returns a dict with keys: status, guest_id, from_date, till_date, count, data
    """
    try:
        conn = get_connection()
        cur = conn.cursor()


    # 2) Fetch paginated list
        cur.execute(f"""
            SELECT 
                rp.rent_payment_id ,
                g.guest_id AS guest_id,                    
                g.name AS guest_name,
                gb.bed_id,
                rp.year,rp.month,
                rp.amount AS amount,
                d.total_due-d.total_paid as balance,
                rp.created_at AS payment_date,
                rp.mode,    
                rp.reference,
                rp.status,
                u.name  AS forwarded_user

            FROM rent_payments rp
            LEFT JOIN guests g 
                ON g.guest_id = rp.guest_id

            LEFT JOIN guests u                      -- ⬅️ JOIN TO GET FORWARDED USER NAME
                ON u.guest_id = rp.current_approver
                
            Left join (
                SELECT
                    guest_id,
                    SUM(due_amount) AS total_due,
                    SUM(amount_paid) AS total_paid
                FROM dues
                GROUP BY guest_id
            ) d ON d.guest_id = rp.guest_id
            
            LEFT JOIN guest_beds AS gb ON g.guest_id = gb.guest_id
                    
            WHERE rp.status IN ('submitted', 'forwarded') and g.status in ('_blank', 'inactive', 'active')

            ORDER BY rp.created_at DESC;


        """)
        rows = cur.fetchall()
        result = []
        

        for r in rows:
            formatted = datetime.strptime(r["payment_date"], "%Y-%m-%d %H:%M:%S").strftime("%#d/%#m/%y")
            result.append({
                "rent_payment_id": r["rent_payment_id"],
                "guest_id": r["guest_id"],                
                "guest_name": r["guest_name"],
                "bed_id": r["bed_id"],
                "amount": r["amount"],
                "balance": r["balance"],
                "status": r["status"],
                "forwarded_user": r["forwarded_user"],
                "month": r["month"],
                "year": r["year"],
                "payment_date":formatted,
                "mode": r["mode"],
                "reference": r["reference"]
            })


        # with open(ITEMS_JSON_PATH, "r", encoding="utf-8") as f:
        #     data = json.load(f)
        return result
    except FileNotFoundError:
        return {"error": "items.json not found"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format"}



def get_processed_payments(    
    authorization: Optional[str] = Header(None),
    search: Optional[str] = None,
    status: Optional[str] = Query(None, regex="^(active|inactive|closed)$"),
    sharing_type: Optional[str] = Query(None, regex="^(brass|silver|golden)$"),
) -> List[Dict]:
    """
    Fetch guest metadata records for the window [till_date - days, till_date].
    Returns a dict with keys: status, guest_id, from_date, till_date, count, data
    """
    try:
        conn = get_connection()
        cur = conn.cursor()


    # 2) Fetch paginated list
        cur.execute(f"""
            SELECT 
                rp.rent_payment_id ,
                g.guest_id AS guest_id,                    
                g.name AS guest_name,
                gb.bed_id,
                rp.year,rp.month,
                rp.amount AS amount,
                d.total_due-d.total_paid as balance,
                rp.created_at AS payment_date,
                rp.mode,    
                rp.reference,
                rp.status,
                u.name  AS forwarded_user

            FROM rent_payments rp
            LEFT JOIN guests g 
                ON g.guest_id = rp.guest_id

            LEFT JOIN guests u                      -- ⬅️ JOIN TO GET FORWARDED USER NAME
                ON u.guest_id = rp.current_approver
                
            Left join (
                SELECT
                    guest_id,
                    SUM(due_amount) AS total_due,
                    SUM(amount_paid) AS total_paid
                FROM dues
                GROUP BY guest_id
            ) d ON d.guest_id = rp.guest_id
            
            LEFT JOIN guest_beds AS gb ON g.guest_id = gb.guest_id
                    
            WHERE rp.status IN ('approved_final','rejected', 'cancelled') and g.status in ('_blank', 'inactive', 'active')

            ORDER BY rp.created_at DESC;


        """)
        rows = cur.fetchall()
        result = []
        

        for r in rows:
            formatted = datetime.strptime(r["payment_date"], "%Y-%m-%d %H:%M:%S").strftime("%#d/%#m/%y")
            result.append({
                "rent_payment_id": r["rent_payment_id"],
                "guest_id": r["guest_id"],                
                "guest_name": r["guest_name"],
                "bed_id": r["bed_id"],
                "amount": r["amount"],
                "balance": r["balance"],
                "status": r["status"],
                "forwarded_user": r["forwarded_user"],
                "month": r["month"],
                "year": r["year"],
                "payment_date":formatted,
                "mode": r["mode"],
                "reference": r["reference"]
            })


        # with open(ITEMS_JSON_PATH, "r", encoding="utf-8") as f:
        #     data = json.load(f)
        return result
    except FileNotFoundError:
        return {"error": "items.json not found"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format"}




@router.get("/guest-assignments")
def list_bed_guest_assignments(
    authorization: Optional[str] = Header(None),
    search: Optional[str] = None,
    status: Optional[str] = Query(None, regex="^(active|inactive|closed)$"),
    sharing_type: Optional[str] = Query(None, regex="^(brass|silver|golden)$"),
) -> List[Dict]:
    """
    Returns LEFT JOIN of beds with guest_beds and guest names.
    Optional filters:
      - search: case-insensitive match on guest_name
      - status: filter by guest status (active|inactive|closed)

    Note: Applying status/search will naturally exclude unassigned beds
    because the filter applies to the joined guest row.
    """
    token = _require_token(authorization)
    _validate_session(token)

    conn = get_connection()
    cur = conn.cursor()
    try:
        where_clauses = []
        params: list = []

        if status:
            where_clauses.append("LOWER(g.status) = ?")
            params.append(str(status).lower())
        if search:
            where_clauses.append("LOWER(g.name) LIKE ?")
            params.append(f"%{str(search).lower().strip()}%")

        # Bed-related filter
        if sharing_type:
            where_clauses.append("LOWER(b.sharing_type) = ?")
            params.append(sharing_type.lower())
        
        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        cur.execute(
            f"""
            SELECT
                b.id AS id,
                b.bed_id AS bed_id,
                b.sharing_type AS bed_sharing_type,
                gra.assignment_id AS assignment_id,
                gra.guest_id AS guest_id,
                g.name AS guest_name,
                gra.assign_date AS assign_date,
                COUNT(gf.face_id) AS face_count 
            FROM beds b
            LEFT JOIN guest_beds gra ON gra.bed_id = b.bed_id
            LEFT JOIN guests g ON g.guest_id = gra.guest_id
            LEFT JOIN guest_faces gf ON g.guest_id = gf.guest_id
            {{WHERE_SQL}}
            GROUP BY b.id, gra.assignment_id
            ORDER BY b.bed_id ASC, gra.assign_date DESC, gra.assignment_id DESC
            """.replace("{WHERE_SQL}", where_sql)
        , params)
        rows = [dict(r) for r in cur.fetchall()]
        return rows
    finally:
        conn.close()





def approve_rent_payment( rent_payment_id, approver, comment=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")

        # Fetch payment
        payment = cur.execute("""
            SELECT guest_id, amount, status, year, month
            FROM rent_payments
            WHERE rent_payment_id = ?
        """, (rent_payment_id,)).fetchone()

        if not payment:
            raise Exception("Payment not found")

        if payment["status"] not in ("submitted", "forwarded"):
            raise Exception("Payment cannot be approved")

        remaining = payment["amount"]

        # Fetch open dues (oldest first)
        dues = cur.execute("""
            SELECT id, due_amount, amount_paid
            FROM dues
            WHERE guest_id = ?
              AND status IN ('open','partial')
            ORDER BY year, month, id
        """, (payment["guest_id"],)).fetchall()

        for d in dues:
            if remaining <= 0:
                break

            balance = d["due_amount"] - d["amount_paid"]
            alloc = min(balance, remaining)

            # allocation
            cur.execute("""
                INSERT INTO rent_payment_allocations
                (rent_payment_id, due_id, allocated_amount)
                VALUES (?,?,?)
            """, (rent_payment_id, d["id"], alloc))

            # update dues
            new_paid = d["amount_paid"] + alloc
            status = "paid" if new_paid >= d["due_amount"] else "partial"

            cur.execute("""
                UPDATE dues
                SET amount_paid = ?, status = ?
                WHERE id = ?
            """, (new_paid, status, d["id"]))

            remaining -= alloc

        # update payment
        cur.execute("""
            UPDATE rent_payments
            SET status='approved_final',
                approved_at=datetime('now'),
                approved_by=?
            WHERE rent_payment_id=?
        """, (approver, rent_payment_id))

        # history
        cur.execute("""
            INSERT INTO rent_approval_history
            (rent_payment_id, acted_by, action, comment)
            VALUES (?,?, 'approved', ?)
        """, (rent_payment_id, approver, comment))

        conn.commit()
        return {
            "success": True,
            "message": "Approve action successfully complete"
        }

    except Exception as e:
        conn.rollback()
        raise e
    


def reject_rent_payment( rent_payment_id, rejected_by, comment):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")

        cur.execute("""
            UPDATE rent_payments
            SET status='rejected'
            WHERE rent_payment_id=?
              AND status IN ('submitted','forwarded')
        """, (rent_payment_id,))

        if cur.rowcount == 0:
            raise Exception("Payment cannot be rejected")

        cur.execute("""
            INSERT INTO rent_approval_history
            (rent_payment_id, acted_by, action, comment)
            VALUES (?,?, 'rejected', ?)
        """, (rent_payment_id, rejected_by, comment))

        conn.commit()
        return {
            "success": True,
            "message": "Reject action successfully complete"
        }
    except:
        conn.rollback()
        raise


def cancel_rent_payment( rent_payment_id, cancelled_by, reason):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")

        payment = cur.execute("""
            SELECT status
            FROM rent_payments
            WHERE rent_payment_id=?
        """, (rent_payment_id,)).fetchone()

        # if not payment or payment["status"] == "approved_final":
        #     raise Exception("Approved payment cannot be cancelled")

        # rollback dues
        allocations = cur.execute("""
            SELECT due_id, allocated_amount
            FROM rent_payment_allocations
            WHERE rent_payment_id=?
        """, (rent_payment_id,)).fetchall()

        for a in allocations:
            cur.execute("""
                UPDATE dues
                SET amount_paid = amount_paid - ?
                WHERE id=?
            """, (a["allocated_amount"], a["due_id"]))

            cur.execute("""
                UPDATE dues
                SET status = CASE
                    WHEN amount_paid <= 0 THEN 'open'
                    WHEN amount_paid < due_amount THEN 'partial'
                    ELSE status
                END
                WHERE id=?
            """, (a["due_id"],))

        cur.execute("""
            DELETE FROM rent_payment_allocations
            WHERE rent_payment_id=?
        """, (rent_payment_id,))

        cur.execute("""
            UPDATE rent_payments
            SET status='cancelled'
            WHERE rent_payment_id=?
        """, (rent_payment_id,))

        cur.execute("""
            INSERT INTO rent_approval_history
            (rent_payment_id, acted_by, action, comment)
            VALUES (?, ?, 'rejected', ?)
        """, (rent_payment_id, cancelled_by, reason))

        conn.commit()
        return {
            "success": True,
            "message": "cancel action successfully complete"
        }
    except:
        conn.rollback()
        raise



def forward_rent_payment(
    rent_payment_id: int,
    from_user: str,
    to_user: str,
    comment: str = None
):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")

        payment = cur.execute("""
            SELECT status
            FROM rent_payments
            WHERE rent_payment_id = ?
        """, (rent_payment_id,)).fetchone()

        if not payment:
            raise Exception("Payment not found")

        if payment["status"] in ("approved_final", "rejected", "cancelled"):
            raise Exception("Payment cannot be forwarded")

        # Update payment
        cur.execute("""
            UPDATE rent_payments
            SET status = 'forwarded',
                current_approver = ?
            WHERE rent_payment_id = ?
        """, (to_user, rent_payment_id))


        # Forward history
        cur.execute("""
            INSERT INTO rent_forward_history
            (rent_payment_id, from_user, to_user, comment)
            VALUES (?, ?, ?, ?)
        """, (rent_payment_id, from_user, to_user, comment))

        conn.commit()
        return {
            "success": True,
            "message": "Forward action successfully complete"
        }
    except Exception as e:
        conn.rollback()
        raise e




def get_onloadaction(guest_id: str)  -> Dict[str, Any]:

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Fetch approval history
        cur.execute("""
            SELECT 
                g.guest_id,
                g.name,
                b.bed_id AS bed_number,
                b.bed_id AS title,
                bed.sharing_type,
                'active' as state,
                balances.id,
                balances.balance AS amount,
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
            where g.guest_id=?
        """, (guest_id,))
        outdata = [dict(r) for r in cur.fetchall()]
        return {
            "success": True,
            "records": outdata
        }
    finally:
        conn.close()


def pay_rent(created_by, guest_id,pay_rent,trx_id,pay_month_year,pay_date,payment_mode,paid_by):
                    
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("BEGIN")

        # 1️⃣ Extract year & month
        try:
            year, month = map(int, pay_month_year.split("-"))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid pay_month_year format (expected YYYY-MM)"
            )

        # 2️⃣ Validate payment mode
        if payment_mode not in ("UPI", "CASH", "IMPS", "DD"):
            raise HTTPException(
                status_code=400,
                detail="Invalid payment mode"
            )

        # 3️⃣ Insert rent payment
        cur.execute("""
            INSERT INTO rent_payments (
                created_by,
                guest_id,
                year,
                month,
                amount,
                mode,
                reference,
                description,
                status,
                created_at
            )
            VALUES (?,?, ?, ?, ?, ?,  ?,?, 'submitted', datetime('now'))
        """, (
            created_by,
            guest_id,
            year,
            month,
            pay_rent,
            payment_mode,
            trx_id,
            paid_by
        ))

        conn.commit()

        return {
            "success": True,
            "message": "Rent payment submitted successfully"
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()




def pay_initial_rent(
    created_by,
    guest_id,
    rent_dueable,
    pay_security,
    pay_rent,
    trx_id,
    pay_month_year,
    pay_date,
    payment_mode,
    paid_by
):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")

        # 1️⃣ Extract year & month
        try:
            year, month = map(int, pay_month_year.split("-"))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid pay_month_year format (expected YYYY-MM)"
            )

        # 2️⃣ Validate payment mode
        if payment_mode not in ("UPI", "CASH", "IMPS", "DD"):
            raise HTTPException(
                status_code=400,
                detail="Invalid payment mode"
            )

        # 3️⃣ Get due_type_ids
        rent_due_type_id = get_due_type_id(cur, "RENT")
        security_due_type_id = get_due_type_id(cur, "SECURITY")

        cur.execute("""
            UPDATE guests
            SET status = 'active'
            WHERE guest_id = ?
        """, (guest_id,))

        # 4️⃣ INSERT DUES (idempotent)
        if rent_dueable and float(rent_dueable) > 0:
            cur.execute("""
                INSERT OR IGNORE INTO dues (
                    guest_id,
                    due_type_id,
                    year,
                    month,
                    due_amount
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                guest_id,
                rent_due_type_id,
                year,
                month,
                rent_dueable
            ))

        if pay_security  and float(pay_security) > 0:
            cur.execute("""
                INSERT OR IGNORE INTO dues (
                    guest_id,
                    due_type_id,
                    year,
                    month,
                    due_amount
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                guest_id,
                security_due_type_id,
                year,
                month,
                pay_security
            ))

        # 5️⃣ UPSERT SECURITY DEPOSIT
        cur.execute("""
            SELECT id FROM security_deposits WHERE guest_id = ?
        """, (guest_id,))
        row = cur.fetchone()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if pay_security and float(pay_security) > 0:
            if row:
                cur.execute("""
                    UPDATE security_deposits
                    SET amount = amount + ?, collected_on = ?
                    WHERE guest_id = ?
                """, (pay_security, now, guest_id))
            else:
                cur.execute("""
                    INSERT INTO security_deposits (
                        guest_id, amount, collected_on
                    )
                    VALUES (?, ?, ?)
                """, (guest_id, pay_security, now))

        # 6️⃣ INSERT RENT PAYMENT
        if pay_rent and float(pay_rent) > 0:
            cur.execute("""
                INSERT INTO rent_payments (
                    created_by,
                    guest_id,
                    year,
                    month,
                    amount,
                    mode,
                    reference,
                    description,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'submitted', datetime('now'))
            """, (
                created_by,
                guest_id,
                year,
                month,
                pay_rent+pay_security,
                payment_mode,
                trx_id,
                paid_by
            ))

        conn.commit()

        return {
            "success": True,
            "message": "Initial rent & security processed successfully"
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()





def get_due_type_id(cur, code: str) -> int:
    cur.execute("SELECT id FROM due_types WHERE code = ?", (code,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=500,
            detail=f"Due type '{code}' not found"
        )
    return row["id"]




def clear_moveout_rent(guest_id,refund_amount,trx_id,pay_month_year,pay_date,payment_mode,paid_by):
    conn = get_connection()
    cur = conn.cursor()

    try:

        # 1️⃣ Extract year & month
        try:
            year, month = map(int, pay_month_year.split("-"))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid pay_month_year format (expected YYYY-MM)"
            )

        cur.execute("""SELECT status FROM guests WHERE guest_id = ? """, (guest_id,))

        row = cur.fetchone()

        if not row:
            raise Exception("Guest not found")

        if row[0] == 'closed':
            # Already settled, do nothing
            return 0



        # --------------------------------------------------
        # 1️⃣ Settle all outstanding dues using ADVANCE + SECURITY
        # --------------------------------------------------
        settlement = GuestDueSettlement(conn)
        settlement.settle_all_dues(guest_id)

        # --------------------------------------------------
        # 2️⃣ Insert SECURITY REFUND DUE (negative)
        # --------------------------------------------------
        cur.execute("""
            INSERT INTO dues (
                guest_id,
                due_type_id,
                year,
                month,
                due_amount,
                amount_paid,
                status
            )
            VALUES (?, 3, ?,?,?, ?, 'paid')
        """, (
            guest_id,
            year,
            month,
            -refund_amount,
            -refund_amount
        ))

        refund_due_id = cur.lastrowid  # ✅ now valid

        # --------------------------------------------------
        # 3️⃣ Store refund payment details (UPI / CASH / BANK)
        # --------------------------------------------------
        cur.execute("""
            INSERT INTO rent_payment_refunds (
                guest_id,
                due_id,
                amount,
                payment_mode,
                reference,
                refunded_on
                
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            guest_id,
            refund_due_id,
            refund_amount,
            payment_mode,
            trx_id,
            pay_date
        ))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            UPDATE security_deposits
            SET refunded_amount = refunded_amount + ?, refunded_on = ?
            WHERE guest_id = ?
        """, (refund_amount, now, guest_id))
        # --------------------------------------------------
        # 4️⃣ Final balance check
        # --------------------------------------------------
        cur.execute("""
            SELECT COALESCE(SUM(due_amount - amount_paid), 0)
            FROM dues
            WHERE guest_id = ?
        """, (guest_id,))
        final_balance = cur.fetchone()[0]

        # --------------------------------------------------
        # 5️⃣ Close guest if fully settled
        # --------------------------------------------------
        if final_balance == 0:
            cur.execute("""
                UPDATE guests
                SET status = 'closed'
                WHERE guest_id = ?
            """, (guest_id,))

        conn.commit()
        return final_balance

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
                

def update_payment_amount(rent_payment_id,amount):
   
    conn = get_connection()
    cur = conn.cursor()
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    #cur = db.cursor()

    # 1️⃣ Fetch existing payment
    cur.execute("""
        SELECT amount, status
        FROM rent_payments
        WHERE rent_payment_id = ?
    """, (rent_payment_id,))

    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Payment not found")

    old_amount, status = row

    # 2️⃣ Optional: block edit if final approved
    if status == "approved_final":
        raise HTTPException(
            status_code=403,
            detail="Final approved payment cannot be edited"
        )

    # 3️⃣ Update payment amount
    cur.execute("""
        UPDATE rent_payments
        SET amount = ?
        WHERE rent_payment_id = ?
    """, (amount, rent_payment_id))


    conn.commit()

    return {
        "success": True,
        "rent_payment_id": rent_payment_id,
        "old_amount": old_amount,
        "new_amount": amount
    }



def list_guest_dues(guest_id, start_date, end_date, page, limit):

    offset = (page - 1) * limit
    conn = get_connection()
    cur = conn.cursor()

    # --- Base query parts ---
    base_query = """
        FROM dues AS a
        JOIN guests AS g ON a.guest_id = g.guest_id
        LEFT JOIN due_types AS dt ON a.due_type_id = dt.id
        WHERE DATE(a.created_at) BETWEEN ? AND ?
    """

    params = [
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    ]

    if guest_id != "all":
        base_query += " AND a.guest_id = ?"
        params.append(guest_id)

    # --- Fetch paginated records ---
    cur.execute(f"""
        SELECT 
            a.id,
            g.name AS guest_name,
            dt.name AS due_type_name,
            a.year,
            a.month,
            a.due_amount,
            a.amount_paid,
            (a.due_amount - a.amount_paid) AS balance,
            a.status,
            a.created_at
        {base_query}
        ORDER BY a.created_at DESC
        LIMIT ? OFFSET ?
    """, [*params, limit, offset])

    records = cur.fetchall()
    data = []

    for index, row in enumerate(records):
        data.append({
            "s_no": offset + index + 1,   # ✅ serial number
            "id": row["id"],
            "guest_name": row["guest_name"],
            "due_type_name": row["due_type_name"],
            "year": row["year"],
            "month": row["month"],
            "due_amount": row["due_amount"],
            "amount_paid": row["amount_paid"],
            "balance": row["balance"],
            "status": row["status"],
            "date": row["created_at"],
        })

    # --- Summary ---
    cur.execute(f"""
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(a.due_amount), 0) AS total_due_amount,
            COALESCE(SUM(a.amount_paid), 0) AS total_amount_paid,
            COALESCE(SUM(a.due_amount - a.amount_paid), 0) AS total_balance
        {base_query}
    """, params)

    summary = cur.fetchone()
    conn.close()

    return {
        "total": summary["total"],
        "page": page,
        "limit": limit,
        "summary": {
            "total_due_amount": summary["total_due_amount"],
            "total_amount_paid": summary["total_amount_paid"],
            "total_balance": summary["total_balance"]
        },
        "data": data
    }




def update_due_amount(due_id,due_amount):
   
    conn = get_connection()
    cur = conn.cursor()
    if due_amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    #cur = db.cursor()

    # 1️⃣ Fetch existing payment
    cur.execute("""
        SELECT due_amount, status
        FROM dues
        WHERE id = ?
    """, (due_id,))

    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Due id not found")

    old_amount, status = row

    # 2️⃣ Optional: block edit if final approved
    if status != "open":
        raise HTTPException(
            status_code=403,
            detail="processed dues records cannot be edited"
        )

    # 3️⃣ Update payment amount
    cur.execute("""
        UPDATE dues
        SET due_amount = ?
        WHERE id = ?
    """, (due_amount, due_id))


    conn.commit()

    return {
        "success": True,
        "id": due_id,
        "old_amount": old_amount,
        "new_amount": due_amount
    }