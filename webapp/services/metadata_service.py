from db.database import get_connection
from datetime import datetime, timedelta
from typing import List, Dict, Optional


def _parse_date(date_str: Optional[str]) -> datetime:
	if not date_str:
		return datetime.utcnow()
	try:
		return datetime.strptime(date_str, "%Y-%m-%d")
	except Exception:
		# fallback to now
		return datetime.utcnow()


def get_guest_metadata_month(guest_id: str, till_date: Optional[str] = None, days: int = 30) -> Dict:
	"""
	Fetch guest metadata records for the window [till_date - days, till_date].

	Returns a dict with keys: status, guest_id, from_date, till_date, count, data
	"""
	end_dt = _parse_date(till_date)
	start_dt = end_dt - timedelta(days=days)

	start_str = start_dt.strftime("%Y-%m-%d")
	end_str = end_dt.strftime("%Y-%m-%d")

	conn = get_connection()
	cur = conn.cursor()

	query = (
		"SELECT name, description, timestamp "
		"FROM guest_metadata WHERE guest_id = ? "
		"AND DATE(timestamp) BETWEEN ? AND ? "
		"ORDER BY timestamp DESC"
	)

	cur.execute(query, (guest_id, start_str, end_str))
	rows = cur.fetchall()
	# rows are sqlite3.Row because get_connection sets row_factory
	# Only include name, description, timestamp as requested
	data = [ {"name": r["name"], "description": r["description"], "timestamp": r["timestamp"]} for r in rows ]

	conn.close()

	return {
		"status": "success",
		"guest_id": guest_id,
		"from_date": start_str,
		"till_date": end_str,
		"count": len(data),
		"data": data,
	}

