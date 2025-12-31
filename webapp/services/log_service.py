from db.database import get_connection
import json
from datetime import datetime

# def search( start_date, end_date, name=None, text=None):
#         if not start_date or not end_date:
#             return {"error": "start_date & end_date are required."}
#         breakpoint();
#         conn = get_connection()
#         cur = conn.cursor()

#         try:
#             where = ["DATE(m.timestamp) BETWEEN DATE(?) AND DATE(?)"]
#             params = [start_date, end_date]

#             if name and name.strip():
#                 where.append("LOWER(m.name) LIKE ?")
#                 params.append(f"%{name.lower().strip()}%")

#             if text and text.strip():
#                 where.append("LOWER(m.description) LIKE ?")
#                 params.append(f"%{text.lower().strip()}%")

#             where_sql = " AND ".join(where)

#             query = f"""
#                 SELECT 
#                     m.meta_id,
#                     m.guest_id,
#                     m.name,
#                     m.description,
#                     m.timestamp
#                 FROM guest_metadata m
#                 WHERE {where_sql}
#                 ORDER BY m.timestamp DESC
#             """
#             breakpoint();
#             cur.execute(query, params)
#             rows = cur.fetchall()

#             # Convert to dict
#             columns = [col[0] for col in cur.description]
#             return [dict(zip(columns, row)) for row in rows]

#         finally:
#             conn.close()

def search(startDate, endDate, guest_id=None, name=None, text=None, page=1, page_size=10):
    if not startDate or not endDate:
        return {"error": "start_date & end_date are required."}

    conn = get_connection()
    cur = conn.cursor()

    try:
        where = ["DATE(m.timestamp) BETWEEN DATE(?) AND DATE(?)"]
        params = [startDate, endDate]

        if guest_id and guest_id.strip():
            if (guest_id != 'owner'):
                where.append("LOWER(m.guest_id) = ?")
                params.append(f"{guest_id.lower().strip()}")

        if name and name.strip():
            where.append("LOWER(m.name) LIKE ?")
            params.append(f"%{name.lower().strip()}%")

        if text and text.strip():
            where.append("LOWER(m.description) LIKE ?")
            params.append(f"%{text.lower().strip()}%")

        where_sql = " AND ".join(where)
        # Count query
        count_sql = f"""
            SELECT COUNT(*) 
            FROM guest_metadata m
            WHERE {where_sql}
        """
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]

        # Pagination
        offset = (page - 1) * page_size

        # Data query
        query = f"""
            SELECT 
                g.name AS guest,
                m.guest_id,
                m.name,
                m.description,
                m.timestamp
            FROM guest_metadata m
            JOIN guests g ON g.guest_id = m.guest_id
            WHERE {where_sql}
            ORDER BY m.timestamp DESC
            LIMIT ? OFFSET ?
        """

        cur.execute(query, params + [page_size, offset])
        rows = cur.fetchall()

        columns = [col[0] for col in cur.description]
        data = [dict(zip(columns, row)) for row in rows]
        return {
            "total": total,
            "data": data
        }

    finally:
        conn.close()

def normalize_timestamp(ts: str | None):
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") \
                        .strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_guest_metadata(meta: dict):
    guest_id = meta.get("guest_id")
    name = meta.get("name")
    description = meta.get("description")
    timestamp = meta.get("timestamp")

    if not guest_id or not name:
        raise ValueError("guest_id and name are required.")

    conn = get_connection()
    cur = conn.cursor()

    timestamp = normalize_timestamp(timestamp)
    try:
        cur.execute(
            """
            INSERT INTO guest_metadata (guest_id, name, description, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (guest_id, name, description, timestamp),
        )
        conn.commit()
        return{
                    "lastrowid": cur.lastrowid,
                    "status": 'success'
                }

    finally:
        conn.close()