from datetime import datetime
from db.database import get_connection


def mark_attendance(data: dict):
    conn = get_connection()
    cur = conn.cursor()
    
    # check guest exists
    cur.execute("SELECT * FROM guests WHERE guest_id=?", (data["guest_id"],))
    guest = cur.fetchone()
    if not guest:
        conn.close()
        return None
    
    if data["method"] not in ["RFID", "Face", "Manual"]:
        conn.close()
        raise ValueError("Invalid method")
    
    ts = data.get("timestamp") or datetime.now().isoformat()
    
    cur.execute("""
        INSERT INTO attendance (guest_id, method, device_id, timestamp)
        VALUES (?, ?, ?, ?)
    """, (data["guest_id"], data["method"], data.get("device_id"), ts))
    
    conn.commit()
    conn.close()
    return {**data, "timestamp": ts}

def get_attendance():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM attendance ORDER BY timestamp DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows



def fetch_attendance(guest_id,role_name, start_date, end_date, page, limit):
    offset = (page - 1) * limit
    conn = get_connection()
    cur = conn.cursor()
    # --- Base query parts ---
    base_query = """
        FROM attendance AS a
        JOIN guests AS g ON a.guest_id = g.guest_id
        LEFT JOIN guest_roles AS gr ON g.guest_id = gr.guest_id
        LEFT JOIN roles AS r ON gr.role_id = r.role_id
        WHERE DATE(a.timestamp) BETWEEN ? AND ?
    """

    params = [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]

    # Optional guest filter
    if guest_id != "all":
        base_query += " AND a.guest_id = ?"
        params.append(guest_id)

    # Optional role filter
    if role_name:
        base_query += " AND LOWER(r.role_name) = ?"
        params.append(role_name.lower().strip())

    # --- Fetch paginated records ---
    cur.execute(f"""
        SELECT 
            a.id,
            a.method,
            a.device_id,
            a.timestamp,
            g.guest_id,
            COALESCE(r.role_name, '-') AS role_name
        {base_query}
        ORDER BY a.timestamp DESC
        LIMIT ? OFFSET ?
    """, [*params, limit, offset])
    records = cur.fetchall()
    data = []

    for row in records:
        timestamp = row["timestamp"]
        if not isinstance(timestamp, str):
            timestamp = timestamp.strftime("%Y-%m-%d %I:%M %p")

        if row["device_id"] == "EXIT_CAM":
            in_time, out_time = None, timestamp
        else:
            in_time, out_time = timestamp, None

        data.append({
            "id": row["id"],
            "guest_id": row["guest_id"],
            "role_name": row["role_name"],
            "method": row["method"],
            "device_id": row["device_id"],
            "in_time": in_time,
            "out_time": out_time,
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


def get_guest_device_logs(guest_id: str, limit: int = 10):
    """
    Fetch latest device-level entries for a guest.
    Returns rows with keys: Device, Entry, Exit
    Uses a single efficient SQL query and minimal post-processing.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            device_id AS Device,
            CASE WHEN device_id = 'LIFT_CAM' THEN timestamp END AS Entry,
            CASE WHEN device_id = 'EXIT_CAM' THEN timestamp END AS Exit
        FROM attendance
        WHERE guest_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (guest_id, limit)
    )

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    # Normalize timestamps to readable strings if needed
    for r in rows:
        for k in ("Entry", "Exit"):
            if r.get(k) is None:
                continue
            # ensure string format (DB stores text isoformat)
            if not isinstance(r[k], str):
                try:
                    r[k] = r[k].strftime("%Y-%m-%d %I:%M %p")
                except Exception:
                    r[k] = str(r[k])

    return rows
