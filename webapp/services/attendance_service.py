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



def fetch_attendance(guest_id, start_date, end_date, page, limit):
    offset = (page - 1) * limit

    conn = get_connection()
    cur = conn.cursor()

    # Fetch paginated attendance
    query = """
        SELECT 
            a.id,
            a.method,
            a.device_id,
            a.timestamp,
            g.guest_id
        FROM attendance AS a
        JOIN guests AS g ON a.guest_id = g.guest_id
        WHERE a.guest_id = ?
          AND DATE(a.timestamp) BETWEEN ? AND ?
        ORDER BY a.timestamp DESC
        LIMIT ? OFFSET ?
    """
    cur.execute(query, (guest_id,start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), limit, offset))
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
            "method": row["method"],
            "device_id": row["device_id"],
            "in_time": in_time,
            "out_time": out_time,
        })

    # Count total records for pagination
    count_query = """
        SELECT COUNT(*) AS total
        FROM attendance
        WHERE guest_id = ? AND DATE(timestamp) BETWEEN ? AND ?
    """
    cur.execute(count_query, (guest_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
    total = cur.fetchone()["total"]

    conn.close()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": data
    }