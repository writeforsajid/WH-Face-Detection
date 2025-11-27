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
                gra.assign_date AS assign_date
            FROM beds b
            LEFT JOIN guest_beds gra ON gra.bed_id = b.bed_id
            LEFT JOIN guests g ON g.guest_id = gra.guest_id
            {{WHERE_SQL}}
            ORDER BY b.bed_id ASC, gra.assign_date DESC, gra.assignment_id DESC
            """.replace("{WHERE_SQL}", where_sql)
        , params)
        rows = [dict(r) for r in cur.fetchall()]
        return rows
    finally:
        conn.close()




@router.get("/guest-attendance")
def list_bed_guest_attendance(
    authorization: Optional[str] = Header(None),
    attendance_date: str = Query(None),  # format YYYY-MM-DD
    search: Optional[str] = None,
    status: Optional[str] = Query(None, regex="^(active|inactive|closed)$"),
    sharing_type: Optional[str] = Query(None, regex="^(brass|silver|golden)$"),
) -> List[Dict]:

    token = _require_token(authorization)
    _validate_session(token)

    conn = get_connection()
    cur = conn.cursor()
    try:
        where_clauses = []
        params: list = []
        attendance_params = [attendance_date]

        # Filters
        if status:
            where_clauses.append("LOWER(g.status) = ?")
            params.append(status.lower())

        if search:
            where_clauses.append("LOWER(g.name) LIKE ?")
            params.append(f"%{search.lower().strip()}%")

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

                    -- PRESENT on selected date
                    CASE 
                        WHEN att_today.guest_id IS NOT NULL THEN 1
                        ELSE 0
                    END AS is_present,

                    -- LEAVE on selected date
                    CASE 
                        WHEN leave_today.guest_id IS NOT NULL THEN 1
                        ELSE 0
                    END AS is_leave,

                    leave_today.leave_id AS leave_id,

                    -- Latest attendance datetime
                    last_att.latest_attendance_datetime,
                    last_att.latest_device_id

                FROM beds b
                LEFT JOIN guest_beds gra 
                    ON gra.bed_id = b.bed_id
                LEFT JOIN guests g 
                    ON g.guest_id = gra.guest_id

                -- ATTENDANCE check (present today)
                LEFT JOIN (
                    SELECT guest_id, MAX(timestamp) AS last_present
                    FROM attendance
                    WHERE DATE(timestamp) = DATE(?)
                    GROUP BY guest_id
                ) AS att_today 
                    ON att_today.guest_id = g.guest_id

                -- LEAVE check (approved leave in leave_calendar_cache)
                LEFT JOIN (
                    SELECT lcc.guest_id, lcc.leave_id
                    FROM leave_calendar_cache lcc
                    JOIN leave_requests lr 
                            ON lr.leave_id = lcc.leave_id
                    WHERE lr.status = 'approved'
                      AND DATE(lcc.leave_date) = DATE(?)
                ) AS leave_today
                    ON leave_today.guest_id = g.guest_id

                -- LATEST attendance & device
                LEFT JOIN (
                    SELECT a1.guest_id,
                           a1.timestamp AS latest_attendance_datetime,
                           a1.device_id AS latest_device_id
                    FROM attendance a1
                    INNER JOIN (
                        SELECT guest_id, MAX(timestamp) AS max_ts
                        FROM attendance
                        GROUP BY guest_id
                    ) a2
                    ON a1.guest_id = a2.guest_id
                    AND a1.timestamp = a2.max_ts
                ) AS last_att
                    ON last_att.guest_id = g.guest_id

                {where_sql}

                ORDER BY b.bed_id ASC, gra.assign_date DESC, gra.assignment_id DESC
           """,
            attendance_params +attendance_params+ params
        )
        return [dict(r) for r in cur.fetchall()]

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
    Expects: { "id": str, "guest_id": str }
    """
    token = _require_token(authorization)
    _validate_session(token)

    id = payload.get("id")
    guest_id = payload.get("guest_id")
    
    if not id or not guest_id:
        raise HTTPException(status_code=400, detail="id and guest_id are required")

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Check if bed exists
        cur.execute("SELECT bed_id FROM beds WHERE id = ?", (id,))
        bed_row = cur.fetchone()
        if not bed_row:
            raise HTTPException(status_code=404, detail="Bed not found")
        
        bed_id = bed_row[0]
        
        # Check if guest exists
        cur.execute("SELECT guest_id, name FROM guests WHERE guest_id = ?", (guest_id,))
        guest_row = cur.fetchone()
        if not guest_row:
            raise HTTPException(status_code=404, detail="Guest not found")
        
        # Check if guest is already assigned to any bed
        cur.execute("SELECT bed_id FROM guest_beds WHERE guest_id = ?", (guest_id,))
        existing_assignment = cur.fetchone()
        if existing_assignment:
            raise HTTPException(
                status_code=400, 
                detail=f"Guest is already assigned to bed {existing_assignment[0]}"
            )
        
        # Check if bed already has a guest assigned
        cur.execute("SELECT guest_id FROM guest_beds WHERE bed_id = ?", (bed_id,))
        existing_guest = cur.fetchone()
        if existing_guest:
            raise HTTPException(
                status_code=400, 
                detail=f"Bed {bed_id} is already occupied by guest {existing_guest[0]}"
            )
        
        # Insert assignment into guest_beds
        assign_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO guest_beds (guest_id, bed_id, assign_date) VALUES (?, ?, ?)",
            (guest_id, bed_id, assign_date)
        )
        
        # Update guest status to 'active' since they're being assigned to a bed
        cur.execute(
            "UPDATE guests SET status = 'active' WHERE guest_id = ?",
            (guest_id,)
        )
        
        conn.commit()
        return {
            "status": "success", 
            "message": f"Guest {guest_id} assigned to bed {bed_id}",
            "assignment": {
                "guest_id": guest_id,
                "bed_id": bed_id,
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
