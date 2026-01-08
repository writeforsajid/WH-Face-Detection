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
from services import rentalmonth_pay_Initial_rent as rpir
from Designs.Chain_of_Responsibility  import TaskContext
from services import rentalmonth_service_models as rsm
from services.google_contact_service import safe_add_or_edit_contact
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

    'active' AS state,

    balances.reference_due_id,
    balances.balance AS amount,

    /* 🔐 Net security paid (received - adjusted - refunded) */
    COALESCE(sec_paid.security_paid, 0) AS security_amount

FROM guests g

/* 💰 Outstanding dues */
JOIN (
    SELECT 
        guest_id,
        MIN(id) AS reference_due_id,
        SUM(due_amount - amount_paid) AS balance
    FROM dues
    GROUP BY guest_id
    HAVING balance > 0
) balances 
    ON balances.guest_id = g.guest_id


/* 🛏 Latest bed assignment */
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


/* 📌 OPTIONAL: expected security from legacy SECURITY dues */
LEFT JOIN (
    SELECT 
        d.guest_id,
        SUM(d.due_amount) AS security_expected
    FROM dues d
    JOIN due_types dt 
        ON d.due_type_id = dt.id
    WHERE dt.code = 'SECURITY'
    GROUP BY d.guest_id
) sec_due 
    ON g.guest_id = sec_due.guest_id


/* 🔐 Security actually paid (correct model) */
LEFT JOIN (
    SELECT
        sa.guest_id,
        SUM(
            CASE
                WHEN st.txn_type = 'received' THEN st.amount
                WHEN st.txn_type IN ('adjusted','refunded') THEN -st.amount
                ELSE 0
            END
        ) AS security_paid
    FROM security_accounts sa
    LEFT JOIN security_transactions st
        ON st.security_id = sa.id
    GROUP BY sa.guest_id
) sec_paid 
    ON g.guest_id = sec_paid.guest_id


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

#############################################################
#   UPDATE CONTACT NUMBER 
#############################################################

        cur.execute("""
                SELECT
                    COALESCE(SUM(d.due_amount - d.amount_paid), 0) AS total_balance,
                    gb.bed_id
                FROM dues d
                LEFT JOIN guest_beds gb
                    ON gb.guest_id = d.guest_id
                WHERE d.guest_id = ?
                AND d.status IN ('open','partial')
                GROUP BY gb.bed_id;
        """, (payment["guest_id"],))
        row = cur.fetchone()
        total_balance = row["total_balance"]
        bedNumber  = row["bed_id"]
        prefix = "AV. "

        if ((total_balance >  0) and bedNumber) : prefix="AV.D. "
        guest_name = prefix  + guest_name + " "+ bedNumber
        safe_add_or_edit_contact(payment["guest_id"], guest_name)

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

    'active' AS state,

    balances.id,
    balances.balance AS amount,

    COALESCE(sec_paid.security_paid, 0) AS security_amount

FROM guests g

/* 🔴 Outstanding dues */
JOIN (
    SELECT 
        guest_id,
        MIN(id) AS id,
        SUM(due_amount - amount_paid) AS balance
    FROM dues
    GROUP BY guest_id
    HAVING SUM(due_amount - amount_paid) > 0
) balances 
    ON balances.guest_id = g.guest_id


/* 🛏 Latest bed assignment */
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


/* 🔐 Actual security paid (NEW STRUCTURE) */
LEFT JOIN (
    SELECT
        sa.guest_id,
        SUM(
            CASE
                WHEN st.txn_type = 'received' THEN st.amount
                WHEN st.txn_type IN ('adjusted','refunded') THEN -st.amount
                ELSE 0
            END
        ) AS security_paid
    FROM security_accounts sa
    LEFT JOIN security_transactions st
        ON st.security_id = sa.id
    GROUP BY sa.guest_id
) sec_paid 
    ON g.guest_id = sec_paid.guest_id

WHERE g.guest_id = ?;
        """, (guest_id,))

        outdata = [dict(r) for r in cur.fetchall()]
        # ----------------------------------
        # Get due_type_id
        # ----------------------------------
        cur.execute("SELECT sharing_type,monthly_rent FROM bed_rent_plan")
        sharing_type_data = [dict(r) for r in cur.fetchall()]

        cur.execute("""
        SELECT b.sharing_type, b.bed_id
        FROM beds b
        LEFT JOIN guest_beds gb ON b.bed_id = gb.bed_id
        WHERE gb.bed_id IS NULL
        ORDER BY b.sharing_type, b.bed_id
        """)

        vacant_beds = [dict(r) for r in cur.fetchall()]

        return {
            "success": True,
            "records": outdata,
            "step2": {
                "sharing_type": sharing_type_data,
                "vacant_beds": vacant_beds
        },
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





def add_dues( guest_id, dues_amount, dues_type, due_month_year, due_date):
    conn = get_connection()
    cur = conn.cursor()

    try:
        # ----------------------------------
        # Parse year & month
        # ----------------------------------
        if len(due_month_year) == 7:  # YYYY-MM
            year, month = map(int, due_month_year.split("-"))
        else:  # YYYY-MM-DD
            dt = datetime.strptime(due_month_year, "%Y-%m-%d")
            year, month = dt.year, dt.month

        # ----------------------------------
        # Get due_type_id
        # ----------------------------------
        cur.execute(
            "SELECT id FROM due_types WHERE code = ?",
            (dues_type,)
        )
        row = cur.fetchone()
        if not row:
            raise Exception("Invalid due type")

        due_type_id = row[0]

        # ----------------------------------
        # Check if due already exists
        # ----------------------------------
        cur.execute("""
            SELECT id, due_amount
            FROM dues
            WHERE guest_id = ?
              AND due_type_id = ?
              AND year = ?
              AND month = ?
        """, (guest_id, due_type_id, year, month))

        existing = cur.fetchone()

        if existing:
            # ----------------------------------
            # UPDATE → increase due amount
            # ----------------------------------
            due_id, old_amount = existing
            new_amount = old_amount + dues_amount

            cur.execute("""
                UPDATE dues
                SET due_amount = ?,
                    created_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_amount, due_id))

            action = "updated"

        else:
            # ----------------------------------
            # INSERT new due
            # ----------------------------------
            cur.execute("""
                INSERT INTO dues (
                    guest_id,
                    due_type_id,
                    year,
                    month,
                    due_amount,
                    amount_paid,
                    status,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, 0, 'open', CURRENT_TIMESTAMP)
            """, (
                guest_id,
                due_type_id,
                year,
                month,
                dues_amount
            ))

            action = "inserted"

        conn.commit()

        return {
            "status": "success",
            "action": action,
            "guest_id": guest_id,
            "year": year,
            "month": month,
            "due_type": dues_type
        }

    except Exception as e:
        conn.rollback()
        return {
            "status": "error",
            "message": str(e)
        }

    finally:
        conn.close()


def pay_initial_rent(
payload: rsm.PayInitialRentRequest
):
    

    conn = get_connection()
    cur = conn.cursor()
    # 🔹 Context explicitly populated
    ctx = TaskContext(
        created_by=payload.created_by,
        guest_id=payload.guest_id,
        guest_name=payload.guest_name,
        rent_dueable=payload.rent_dueable,
        security_due=payload.security_due,
        pay_security=payload.pay_security,
        pay_rent=payload.pay_rent,
        trx_id=payload.trx_id,
        pay_month_year=payload.pay_month_year,
        pay_date=payload.pay_date,
        payment_mode=payload.payment_mode,
        paid_by=payload.paid_by,
        activate_user=payload.activate_user,
        send_email=payload.send_email,
        roomType=payload.roomType,
        roomBed=payload.roomBed,
        roomAssignedAt=payload.roomAssignedAt,
        bdasign=payload.bdasign,
        rent_payment_id=0,
        approved_payment=payload.approved_payment,
        bedNumber=payload.bedNumber,
        admission_date= payload.admission_date,
        pay_advance=payload.pay_advance,
        total_payment= payload.total_payment,
        rent_start_date= payload.rent_start_date,
        conn=conn,
        cur=cur
    )

    # TODO: Chain of responsibilities
    workflow = rpir.ParseMonthTask(                         # Split Month/Year
        rpir.ValidatePaymentModeTask(                       # in ("UPI", "CASH", "IMPS", "DD"):
            rpir.ActivateGuestTask(                         # UPDATE guests SET status='active'
                rpir.RentPaymentTask(                           # Add/Update RENT DUES
                    rpir.SecurityDueTask(                   # Add/Update SECURITY DUES
                        rpir.AdvanceDueTask( 
                            rpir.RentDueTask(
                                rpir.AssignBed(
                                    rpir.ApprovePayment(
                                            rpir.AddEditPhoneNoToContact()
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )
    )

    try:
        cur.execute("BEGIN")
       
        workflow.execute(ctx)
        conn.commit()

        return {
            "success": True,
            "message": "Initial rent & security processed successfully"
        }

    except StopIteration:
        # intentional skip (nothing to pay)
        conn.commit()
        return {
            "success": True,
            "message": "No payable action"
        }

    except Exception as e:
        conn.rollback()
        raise

    finally:
        conn.close()

    
def pay_intermediate_security(payload: rsm.SecurityRequest):
    conn = get_connection()
    cur = conn.cursor()

    ctx = TaskContext(
        created_by=payload.created_by,
        guest_id=payload.guest_id,
        txn_type=payload.txn_type,
        pay_security=payload.pay_security,
        trx_id=payload.trx_id,
        pay_date=payload.pay_date,
        payment_mode=payload.payment_mode,
        sec_remarks=payload.sec_remarks,
        conn=conn,
        cur=cur
    )

    workflow = rpir.SecurityDueTaskPartTwo()
    workflow.execute(ctx)

    conn.commit()
    conn.close()   # ✅ IMPORTANT

    return {"status": "success"}


    
def pay_intermediate_advance(payload: rsm.AdvanceRequest):
    conn = get_connection()
    cur = conn.cursor()

    ctx = TaskContext(
        created_by=payload.created_by,
        guest_id=payload.guest_id,
        txn_type=payload.txn_type,
        pay_advance=payload.pay_advance,
        trx_id=payload.trx_id,
        pay_date=payload.pay_date,
        payment_mode=payload.payment_mode,
        sec_remarks=payload.sec_remarks,
        conn=conn,
        cur=cur
    )

    workflow = rpir.AdvanceDueTaskPartTwo()
    workflow.execute(ctx)

    conn.commit()
    conn.close()   # ✅ IMPORTANT

    return {"status": "success"}


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
        # 4️⃣ Final balance check
        # --------------------------------------------------
        cur.execute("""
            SELECT COALESCE(SUM(due_amount - amount_paid), 0)
            FROM dues
            WHERE guest_id = ?
        """, (guest_id,))
        final_balance = cur.fetchone()[0]
        # --------------------------------------------------
        # 2️⃣ Insert SECURITY REFUND DUE (negative)
        # --------------------------------------------------
        if (final_balance > 0) :
            cur.execute("""
                INSERT OR IGNORE INTO dues ( guest_id,due_type_id,year,month,due_amount,amount_paid,status)
                VALUES (?, 10, ?,?,?, 0, 'adjusted')
            """, (
                guest_id,
                year,
                month,
                -final_balance
            ))
        if (final_balance <= 0) :
            cur.execute("""
                INSERT OR IGNORE INTO dues ( guest_id,due_type_id,year,month,due_amount,amount_paid,status)
                VALUES (?, 10, ?,?,0, ?, 'adjusted')
            """, (
                guest_id,
                year,
                month,
                final_balance
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
        #----Fix later
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


def duesofguest( guest_id,year,month,due_type_id):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT
            guest_id,
            due_type_id,
            year,
            month,
            due_amount,
            amount_paid,
            status
        FROM dues
        WHERE 1 = 1
    """

    params = []

    if guest_id:
        query += " AND guest_id = ?"
        params.append(guest_id)

    if due_type_id is not None:
        query += " AND due_type_id = ?"
        params.append(due_type_id)

    if year:
        query += " AND year = ?"
        params.append(year)

    if month:
        query += " AND month = ?"
        params.append(month)

    cur.execute(query, params)
    rows = cur.fetchall()
    data=[
        {
            "guest_id": r[0],
            "due_type_id": r[1],
            "year": r[2],
            "month": r[3],
            "due_amount": r[4],
            "amount_paid": r[5],
            "status": r[6]
        }
        for r in rows
    ]
    params = []
    query ="""
             SELECT
            COUNT(*) AS total,
            COALESCE(SUM(a.due_amount), 0) AS total_due_amount,
            COALESCE(SUM(a.amount_paid), 0) AS total_amount_paid,
            COALESCE(SUM(a.due_amount - a.amount_paid), 0) AS total_balance,
            COALESCE(SUM(CASE WHEN a.due_type_id = 3 THEN a.due_amount ELSE 0 END),0) AS security_amount
            FROM dues AS a
            JOIN guests AS g ON a.guest_id = g.guest_id
            LEFT JOIN due_types AS dt ON a.due_type_id = dt.id
            WHERE 1 = 1 
            """
    if guest_id:
        query += " AND a.guest_id = ?"
        params.append(guest_id)

        # --- Summary ---
    cur.execute(query, params)

    summary = cur.fetchone()

    
    conn.close()

    return {
    "total": summary["total"],
    "summary": {
        "total_due_amount": summary["total_due_amount"],
        "total_amount_paid": summary["total_amount_paid"],
        "total_balance": summary["total_balance"],
        "total_security_paid": summary["security_amount"]
    },
    "data": data
    }




def list_guest_payments(guest_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        WITH dues_with_cumulative AS (
            SELECT
                d.id AS due_id,
                d.due_type_id,
                d.year,
                d.month,
                d.due_amount,
                d.amount_paid,
                (d.due_amount - d.amount_paid) AS bal,
                SUM(d.due_amount - d.amount_paid) OVER (
                    ORDER BY d.year, d.month ASC
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS cumulative_bal
            FROM dues d
            WHERE d.guest_id = ?
        )
        SELECT
            dwc.*,
            COALESCE(rpa.rent_payment_id, 0)    AS rent_payment_id,
            COALESCE(rpa.allocated_amount, 0)   AS allocated_amount,
            COALESCE(rp.amount, 0)              AS payment_amount,
            COALESCE(rp.status, 'unpaid')       AS payment_status,
            COALESCE(rp.created_at, '')         AS payment_date
        FROM dues_with_cumulative dwc
        LEFT JOIN rent_payment_allocations rpa
            ON rpa.due_id = dwc.due_id
        LEFT JOIN rent_approval_history rah
            ON rah.rent_payment_id = rpa.rent_payment_id
            AND rah.action = 'approved'
        LEFT JOIN rent_payments rp
            ON rp.rent_payment_id = rpa.rent_payment_id 
        ORDER BY dwc.year, dwc.month ASC, rent_payment_id DESC
    """, (guest_id,))

    rows = cur.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="Payments + Dues not found")

    # ================================
    # 1️⃣ GROUP DATA
    # ================================
    payment_map = {}
    grouped = []

    for r in rows:
        r = dict(r)
        pid = r["rent_payment_id"]

        if pid not in payment_map:
            payment_map[pid] = {
                "rent_payment_id": pid,
                "payment_amount": r["payment_amount"],
                "payment_status": r["payment_status"],
                "payment_date": r["payment_date"],
                "total_allocated": 0,
                "cumulative_bal": r["cumulative_bal"],
                "dues": []
            }
            grouped.append(payment_map[pid])

        payment_map[pid]["total_allocated"] += r["allocated_amount"]
        payment_map[pid]["dues"].append({
            "due_id": r["due_id"],
            "due_type_id": r["due_type_id"],
            "year": r["year"],
            "month": r["month"],
            "due_amount": r["due_amount"],
            "amount_paid": r["amount_paid"],
            "bal": r["bal"]
        })

    # ================================
    # 2️⃣ CUSTOM SORT (KEY REQUIREMENT)
    # ================================
    grouped.sort(
        key=lambda x: (x["rent_payment_id"] != 0, -x["rent_payment_id"])
    )

    conn.close()
    return grouped


def get_rent_receipt(rent_payment_id):
    conn = get_connection()
    cur = conn.cursor()
    SQL_QUERY="""
        SELECT
            rp.rent_payment_id,
            rp.amount              AS payment_amount,
            rp.created_at          AS payment_date,
            g.name                 AS tenant_name,
            d.id                   AS due_id,
            dt.name                AS due_type,
            printf('%02d-%02d-%04d', 1, d.month, d.year)  AS period_from,
            date(
                printf('%04d-%02d-01', d.year, d.month),
                '+1 month', '-1 day'
            ) AS period_to,
            rpa.allocated_amount   AS settled_amount
        FROM rent_payments rp
        JOIN rent_payment_allocations rpa
            ON rpa.rent_payment_id = rp.rent_payment_id
        JOIN dues d
            ON d.id = rpa.due_id
        LEFT JOIN due_types dt
            ON dt.id = d.due_type_id
        LEFT JOIN guests g
            ON g.guest_id = rp.guest_id
        WHERE rp.rent_payment_id = ?
        ORDER BY d.year, d.month;
"""
    cur.execute(SQL_QUERY, (rent_payment_id,))
    rows = cur.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="Receipt not found")
    header = {
        "rent_payment_id": rows[0]["rent_payment_id"],
        "amount": rows[0]["payment_amount"],
        "address": "B-23A, Noor Nagar Ext, Jamia Nagar, Okhla",
        "landlord_name": "Sajida",
        "payment_date": rows[0]["payment_date"],
        "tenant_name": rows[0]["tenant_name"],
        "dues": []
    }

    for r in rows:
        header["dues"].append({
            "due_type": r["due_type"],
            "period_from": r["period_from"],
            "period_to": r["period_to"],
            "settled_amount": r["settled_amount"]
        })

    conn.close()
    return header




    