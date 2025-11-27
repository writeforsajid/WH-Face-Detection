from db.database import get_connection
from datetime import datetime

def apply_leave_service(req):
    conn = get_connection()
    cur = conn.cursor()
    # 1) Validations
    start = datetime.strptime(req.start_date, "%Y-%m-%d")
    end = datetime.strptime(req.end_date, "%Y-%m-%d")
    today = datetime.now().date()

    if start.date() < today:
        raise Exception("Start date cannot be in the past.")

    if end <= start:
        raise Exception("End date must be greater than start date.")

    # 2) Check overlapping leave
    cur.execute("""
        SELECT 1 FROM leave_requests
        WHERE guest_id = ? 
        AND status IN ('pending','approved')
        AND NOT (date(end_date) < date(?) OR date(start_date) > date(?))
    """, (req.guest_id, req.start_date, req.end_date))

    if cur.fetchone():
        raise Exception("You already have a pending/approved leave in this date range.")

    # 3) Insert into DB
    cur.execute("""
        INSERT INTO leave_requests
        (guest_id, leave_type_id, start_date, end_date, reason, applied_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        req.guest_id,
        req.leave_type_id,
        req.start_date,
        req.end_date,
        req.reason,
        req.guest_id
    ))
    leave_id = cur.lastrowid   # ← Get the new leave_id
    #conn.commit()
    cur.execute("""
        UPDATE leave_requests
        SET status = 'approved',
            approved_by = ?,
            approved_on = datetime('now')
        WHERE leave_id = ?
                            """, (req.guest_id,leave_id))
    conn.commit()

    return {"status": "success", "message": "Leave applied successfully"}


def get_my_leaves(guest_id, startDate, endDate, page, pageSize):
    conn = get_connection()
    cur = conn.cursor()

    where = ["guest_id = ?"]
    params = [guest_id]

    # Optional date filters
    if startDate:
        where.append("date(start_date) >= date(?)")
        params.append(startDate)

    if endDate:
        where.append("date(end_date) <= date(?)")
        params.append(endDate)

    where_clause = " AND ".join(where)

    # Pagination
    offset = (page - 1) * pageSize

    # 1) Count total
    cur.execute(f"""
        SELECT COUNT(*)
        FROM leave_requests
        WHERE {where_clause}
    """, params)

    total = cur.fetchone()[0]

    # 2) Fetch paginated list
    cur.execute(f"""
        SELECT 
            leave_id,    
            leave_type_id,
            start_date,
            end_date,
            reason,
            status
        FROM leave_requests
        WHERE {where_clause}
        ORDER BY applied_on DESC
        LIMIT ? OFFSET ?
    """, params + [pageSize, offset])

    rows = cur.fetchall()
    conn.close()

    return {
        "success": True,
        "total": total,
        "page": page,
        "pageSize": pageSize,
        "data": [dict(zip([
            "leave_id", "leave_type_id", "start_date", "end_date",
            "reason", "status"
        ], r)) for r in rows]
    }



def get_unapproved_leaves( startDate, endDate,page, pageSize):
    conn = get_connection()
    cur = conn.cursor()

    where = []
    params = []

    # Optional date filters
    if startDate:
        where.append("date(start_date) >= date(?)")
        params.append(startDate)

    if endDate:
        where.append("date(end_date) <= date(?)")
        params.append(endDate)

    where_clause = " AND ".join(where)


    # Pagination
    offset = (page - 1) * pageSize
    
    # 1) Count total
    cur.execute(f"""
        SELECT COUNT(*)
        FROM leave_requests
        WHERE {where_clause}
    """, params)

    total = cur.fetchone()[0]

    # 2) Fetch paginated list
    cur.execute(f"""
        SELECT 
            leave_id,    
            leave_type_id,
            start_date,
            end_date,
            reason,
            status
        FROM leave_requests
        WHERE {where_clause}
        ORDER BY applied_on DESC
        LIMIT ? OFFSET ?        
    """, params + [pageSize, offset])

    rows = cur.fetchall()
    conn.close()
    return {
        "success": True,
        "total": total,
        "page": page,
        "pageSize": pageSize,
        "data": [dict(zip([
            "leave_id", "leave_type_id", "start_date", "end_date",
            "reason", "status"
        ], r)) for r in rows]
    }
