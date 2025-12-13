from db.database import get_connection
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from utilities.environment_variables import load_environment
import sqlite3,os
import json
from pathlib import Path
#load_environment(env_path);

load_environment("./../data/.env.webapp")
DB_PATH=os.getenv("DB_PATH")
if DB_PATH is None: DB_PATH = "./../data/WhiteHouse.db"
DB_LOCAL_PATH = Path("./../data/WhiteHouse.db")  # your existing path
ITEMS_JSON_PATH = DB_LOCAL_PATH.with_name("items.json")  # same folder, sibling file





from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional, List, Dict
from db.database import get_connection
from datetime import datetime, timezone

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
                "label": r["name"] +' (Bed: '+ r["current_bed"] +')',
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
                
            LEFT JOIN dues d 
                ON d.guest_id = rp.guest_id
                AND d.year = rp.year
                AND d.month = rp.month
            
            LEFT JOIN guest_beds AS gb ON g.guest_id = gb.guest_id
                    
            WHERE rp.status IN ('submitted', 'forwarded')

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


