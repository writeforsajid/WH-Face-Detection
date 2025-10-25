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
