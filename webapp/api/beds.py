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

@router.get("/stats")
def get_beds_stats(authorization: Optional[str] = Header(None)) -> Dict[str, int]:
    """
    Return counts of beds using guest_beds (current assignment table):
      - total: hardcoded to 83 (as requested)
      - occupied: total number of rows in guest_beds (all assignments)
      - vacant: total - occupied

    Requires a valid bearer token.
    """
    token = _require_token(authorization)
    _validate_session(token)

    TOTAL_BEDS = 83  # Hardcoded total as per requirement
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Occupied beds: count all rows in guest_beds
        cur.execute("SELECT COUNT(*) FROM guest_beds")
        occupied = int(cur.fetchone()[0] or 0)

        total = TOTAL_BEDS
        vacant = max(total - occupied, 0)

        return {"total": total, "occupied": occupied, "vacant": vacant}
    finally:
        conn.close()


@router.get("/guest-assignments")
def list_bed_guest_assignments(
    authorization: Optional[str] = Header(None),
    search: Optional[str] = None,
    status: Optional[str] = Query(None, regex="^(active|inactive|closed)$"),
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

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        cur.execute(
            f"""
            SELECT
                b.bed_id AS bed_id,
                b.bed_name AS bed_name,
                b.description AS bed_description,
                gra.assignment_id AS assignment_id,
                gra.guest_id AS guest_id,
                g.name AS guest_name,
                gra.assign_date AS assign_date
            FROM beds b
            LEFT JOIN guest_beds gra ON gra.bed_name = b.bed_name
            LEFT JOIN guests g ON g.guest_id = gra.guest_id
            {{WHERE_SQL}}
            ORDER BY b.bed_name ASC, gra.assign_date DESC, gra.assignment_id DESC
            """.replace("{WHERE_SQL}", where_sql)
        , params)
        rows = [dict(r) for r in cur.fetchall()]
        return rows
    finally:
        conn.close()


# Unassign a guest from a bed (delete guest_beds row)
from fastapi import Body

@router.post("/assign")
def assign_guest_to_bed(
    payload: dict = Body(...),
    authorization: Optional[str] = Header(None)
):
    """
    Assign a guest to a bed by inserting into guest_beds table.
    Expects: { "bed_id": str, "guest_id": str }
    """
    token = _require_token(authorization)
    _validate_session(token)

    bed_id = payload.get("bed_id")
    guest_id = payload.get("guest_id")
    
    if not bed_id or not guest_id:
        raise HTTPException(status_code=400, detail="bed_id and guest_id are required")

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Check if bed exists
        cur.execute("SELECT bed_name FROM beds WHERE bed_id = ?", (bed_id,))
        bed_row = cur.fetchone()
        if not bed_row:
            raise HTTPException(status_code=404, detail="Bed not found")
        
        bed_name = bed_row[0]
        
        # Check if guest exists
        cur.execute("SELECT guest_id, name FROM guests WHERE guest_id = ?", (guest_id,))
        guest_row = cur.fetchone()
        if not guest_row:
            raise HTTPException(status_code=404, detail="Guest not found")
        
        # Check if guest is already assigned to any bed
        cur.execute("SELECT bed_name FROM guest_beds WHERE guest_id = ?", (guest_id,))
        existing_assignment = cur.fetchone()
        if existing_assignment:
            raise HTTPException(
                status_code=400, 
                detail=f"Guest is already assigned to bed {existing_assignment[0]}"
            )
        
        # Check if bed already has a guest assigned
        cur.execute("SELECT guest_id FROM guest_beds WHERE bed_name = ?", (bed_name,))
        existing_guest = cur.fetchone()
        if existing_guest:
            raise HTTPException(
                status_code=400, 
                detail=f"Bed {bed_name} is already occupied by guest {existing_guest[0]}"
            )
        
        # Insert assignment into guest_beds
        assign_date = datetime.now().strftime("%Y-%m-%d")
        cur.execute(
            "INSERT INTO guest_beds (guest_id, bed_name, assign_date) VALUES (?, ?, ?)",
            (guest_id, bed_name, assign_date)
        )
        
        # Update guest status to 'active' since they're being assigned to a bed
        cur.execute(
            "UPDATE guests SET status = 'active' WHERE guest_id = ?",
            (guest_id,)
        )
        
        conn.commit()
        return {
            "status": "success", 
            "message": f"Guest {guest_id} assigned to bed {bed_name}",
            "assignment": {
                "guest_id": guest_id,
                "bed_name": bed_name,
                "assign_date": assign_date
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/unassign")
def unassign_guest_from_bed(
    payload: dict = Body(...),
    authorization: Optional[str] = Header(None)
):
    """
    Unassign a guest from a bed by deleting the guest_beds row for the given guest_id (regardless of bed).
    Expects: { "guest_id": str }
    """
    token = _require_token(authorization)
    _validate_session(token)

    guest_id = payload.get("guest_id")
    if not guest_id:
        raise HTTPException(status_code=400, detail="guest_id required")

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Check if guest is assigned to any bed in guest_beds
        cur.execute("SELECT 1 FROM guest_beds WHERE guest_id = ? LIMIT 1", (guest_id,))
        exists = cur.fetchone()
        if not exists:
            return {"status": "not-assigned", "message": "Guest is not assigned to any bed."}
        # Delete the assignment for this guest (all beds, if multiple)
        cur.execute(
            "DELETE FROM guest_beds WHERE guest_id = ?",
            (guest_id,)
        )
        # Update guest status to 'inactive' when unassigned from bed
        cur.execute(
            "UPDATE guests SET status = 'inactive' WHERE guest_id = ?",
            (guest_id,)
        )
        conn.commit()
        return {"status": "success", "message": "Guest unassigned from bed(s)"}
    finally:
        conn.close()
