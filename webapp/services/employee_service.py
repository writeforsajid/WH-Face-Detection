from db.database import get_connection
from datetime import datetime

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