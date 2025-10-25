# All beds array for 5 floors, 4 flats per floor, 2 rooms per flat, 3 beds per room
# Format: (bed_no, description)

import sqlite3
import os

# Path to the SQLite database
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'WhiteHouse.db'))

beds = [
        ("001/1/1", "Room 001 - Bed 1"),
    ("001/1/2", "Room 001 - Bed 2"),
    ("001/1/3", "Room 001 - Bed 3"),
    ("002/1/1", "Room 002 - Bed 1"),
    ("002/1/2", "Room 002 - Bed 2"),
    ("002/1/2", "Room 002 - Bed 3"),
    ("002/2/1", "Room 002 - Bed 1"),
    ("002/2/2", "Room 002 - Bed 2"),
    ("002/2/3", "Room 002 - Bed 3"),
    ("103/1/1", "Floor 1 Flat 3 Room 1 Bed 1"),
    ("103/1/2", "Floor 1 Flat 3 Room 1 Bed 2"),
    ("103/2/1", "Floor 1 Flat 3 Room 2 Bed 1"),
    ("103/2/2", "Floor 1 Flat 3 Room 2 Bed 2"),
    ("103/2/3", "Floor 1 Flat 3 Room 2 Bed 3"),
    ("104/1/1", "Floor 1 Flat 4 Room 1 Bed 1"),
    ("104/1/2", "Floor 1 Flat 4 Room 1 Bed 2"),
    ("104/2/1", "Floor 1 Flat 4 Room 2 Bed 1"),
    ("104/2/2", "Floor 1 Flat 4 Room 2 Bed 2"),
    ("104/2/3", "Floor 1 Flat 4 Room 2 Bed 3"),
    ("203/1/1", "Floor 2 Flat 3 Room 1 Bed 1"),
    ("203/1/2", "Floor 2 Flat 3 Room 1 Bed 2"),
    ("203/2/1", "Floor 2 Flat 3 Room 2 Bed 1"),
    ("203/2/2", "Floor 2 Flat 3 Room 2 Bed 2"),
    ("203/2/3", "Floor 2 Flat 3 Room 2 Bed 3"),
    ("204/1/1", "Floor 2 Flat 4 Room 1 Bed 1"),
    ("204/1/2", "Floor 2 Flat 4 Room 1 Bed 2"),
    ("204/2/1", "Floor 2 Flat 4 Room 2 Bed 1"),
    ("204/2/2", "Floor 2 Flat 4 Room 2 Bed 2"),
    ("204/2/3", "Floor 2 Flat 4 Room 2 Bed 3"),
    ("303/1/1", "Floor 3 Flat 3 Room 1 Bed 1"),
    ("303/1/2", "Floor 3 Flat 3 Room 1 Bed 2"),
    ("303/2/1", "Floor 3 Flat 3 Room 2 Bed 1"),
    ("303/2/2", "Floor 3 Flat 3 Room 2 Bed 2"),
    ("303/2/3", "Floor 3 Flat 3 Room 2 Bed 3"),
    ("304/1/1", "Floor 3 Flat 4 Room 1 Bed 1"),
    ("304/1/2", "Floor 3 Flat 4 Room 1 Bed 2"),
    ("304/2/1", "Floor 3 Flat 4 Room 2 Bed 1"),
    ("304/2/2", "Floor 3 Flat 4 Room 2 Bed 2"),
    ("304/2/3", "Floor 3 Flat 4 Room 2 Bed 3"),
    ("401/1/1", "Floor 4 Flat 1 Room 1 Bed 1"),
    ("401/1/2", "Floor 4 Flat 1 Room 1 Bed 2"),
    ("401/1/3", "Floor 4 Flat 1 Room 1 Bed 3"),
    ("401/2/1", "Floor 4 Flat 1 Room 2 Bed 1"),
    ("401/2/2", "Floor 4 Flat 1 Room 2 Bed 2"),
    ("401/2/3", "Floor 4 Flat 1 Room 2 Bed 3"),
    ("402/1/1", "Floor 4 Flat 2 Room 1 Bed 1"),
    ("402/1/2", "Floor 4 Flat 2 Room 1 Bed 2"),
    ("402/1/3", "Floor 4 Flat 2 Room 1 Bed 3"),
    ("402/2/1", "Floor 4 Flat 2 Room 2 Bed 1"),
    ("402/2/2", "Floor 4 Flat 2 Room 2 Bed 2"),
    ("402/2/3", "Floor 4 Flat 2 Room 2 Bed 3"),
    ("403/1/1", "Floor 4 Flat 3 Room 1 Bed 1"),
    ("403/1/2", "Floor 4 Flat 3 Room 1 Bed 2"),
    ("403/2/1", "Floor 4 Flat 3 Room 2 Bed 1"),
    ("403/2/2", "Floor 4 Flat 3 Room 2 Bed 2"),
    ("403/2/3", "Floor 4 Flat 3 Room 2 Bed 3"),
    ("404/1/1", "Floor 4 Flat 4 Room 1 Bed 1"),
    ("404/1/2", "Floor 4 Flat 4 Room 1 Bed 2"),
    ("404/2/1", "Floor 4 Flat 4 Room 2 Bed 1"),
    ("404/2/2", "Floor 4 Flat 4 Room 2 Bed 2"),
    ("404/2/3", "Floor 4 Flat 4 Room 2 Bed 3"),
    ("501/1/1", "Floor 5 Flat 1 Room 1 Bed 1"),
    ("501/1/2", "Floor 5 Flat 1 Room 1 Bed 2"),
    ("501/1/3", "Floor 5 Flat 1 Room 1 Bed 3"),
    ("501/2/1", "Floor 5 Flat 1 Room 2 Bed 1"),
    ("501/2/2", "Floor 5 Flat 1 Room 2 Bed 2"),
    ("501/2/3", "Floor 5 Flat 1 Room 2 Bed 3"),
    ("502/1/1", "Floor 5 Flat 2 Room 1 Bed 1"),
    ("502/1/2", "Floor 5 Flat 2 Room 1 Bed 2"),
    ("502/1/3", "Floor 5 Flat 2 Room 1 Bed 3"),
    ("502/2/1", "Floor 5 Flat 2 Room 2 Bed 1"),
    ("502/2/2", "Floor 5 Flat 2 Room 2 Bed 2"),
    ("502/2/3", "Floor 5 Flat 2 Room 2 Bed 3"),
    ("503/1/1", "Floor 5 Flat 3 Room 1 Bed 1"),
    ("503/1/2", "Floor 5 Flat 3 Room 1 Bed 2"),
    ("503/2/1", "Floor 5 Flat 3 Room 2 Bed 1"),
    ("503/2/2", "Floor 5 Flat 3 Room 2 Bed 2"),
    ("503/2/3", "Floor 5 Flat 3 Room 2 Bed 3"),
    ("504/1/1", "Floor 5 Flat 4 Room 1 Bed 1"),
    ("504/1/2", "Floor 5 Flat 4 Room 1 Bed 2"),
    ("504/2/1", "Floor 5 Flat 4 Room 2 Bed 1"),
    ("504/2/2", "Floor 5 Flat 4 Room 2 Bed 2"),
    ("504/2/3", "Floor 5 Flat 4 Room 2 Bed 3"),
]

# Connect to database and insert beds
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Insert beds into the database
cursor.executemany(
    "INSERT OR IGNORE INTO beds (bed_no, description) VALUES (?, ?)",
    beds
)

conn.commit()
conn.close()

print(f"✅ Successfully inserted {len(beds)} beds into the database!")
