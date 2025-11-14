from db.database import get_connection
import json
# from datetime import datetime

def get_appconfig_by_name(name: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name, description FROM appconfig WHERE name = ?", (name,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if not result:
        return None

    # Parse JSON field if stored as JSON
    try:
        result["description"] = json.loads(result["description"])
    except Exception:
        pass

    return result