from db.database import get_connection
from datetime import datetime


def get_employees(page=1, limit=20, search: str | None = None, status: str | None = None):
    """
    Return paginated guests joined with role and bed info.
    Columns: guest_id, name, guest_type, bed_id, status
    Supports optional filters:
      - search: case-insensitive substring match on name
      - status: one of ('active','inactive','closed')
    """
    
    offset = (page - 1) * limit
    conn = get_connection()
    # conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Build WHERE filters dynamically
    where_clauses = ["LOWER(r.role_name) = 'employee'"]  # 👈 force only employees
    # where_clauses = []  # 👈 force only employees
    params = []
    
    if status:
        st = str(status).lower().strip()
        if st in ("active", "inactive", "closed"):
            where_clauses.append("LOWER(g.status) = ?")
            params.append(st)

    if search:
        where_clauses.append("LOWER(g.name) LIKE ?")
        params.append(f"%{search.lower().strip()}%")

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # --- ⚡ Optimized query ---
    # Use LEFT JOIN to include guests even if role/bed missing
    # Use COALESCE for readable defaults
    base_query = f"""
        FROM guests AS g
        LEFT JOIN guest_roles AS gr ON g.guest_id = gr.guest_id
        LEFT JOIN roles AS r ON gr.role_id = r.role_id
        LEFT JOIN guest_beds AS gb ON g.guest_id = gb.guest_id
        LEFT JOIN beds AS b ON gb.bed_id = b.bed_id
        {where_sql}
    """

    # --- total count for pagination ---
    cur.execute(f"SELECT COUNT(DISTINCT g.guest_id) AS cnt {base_query}", params)
    total = cur.fetchone()["cnt"]
    total_pages = (total + limit - 1) // limit if limit else 1

    # --- main data query ---
    cur.execute(
        f"""
        SELECT 
            g.guest_id,
            g.name,
            COALESCE(r.role_name, '-') AS guest_type,
            COALESCE(b.bed_id, '-') AS bed_no,
            g.status
        {base_query}
        GROUP BY g.guest_id
        ORDER BY g.name ASC
        LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    )

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "items": rows,
    }





def get_active_employee():
    conn = get_connection()
    cur = conn.cursor()
    query = """
        SELECT 
            g.guest_id as id,
            g.name
        FROM guests AS g
        LEFT JOIN guest_roles AS gr ON g.guest_id = gr.guest_id
        LEFT JOIN roles AS r ON gr.role_id = r.role_id
        WHERE r.role_name = 'employee' AND g.status = 'active'
        ORDER BY id DESC
    """
    cur.execute(query)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows