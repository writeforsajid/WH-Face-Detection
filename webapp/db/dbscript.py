import sqlite3
import face_recognition 
import json
import os
from pathlib import Path
import random
from datetime import datetime, timedelta

# Connect (creates file WhiteHouse.db if not exists)
DB_PATH = "./data/WhiteHouse_Fresh.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1️⃣ Guests Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS guests (
    guest_id    VARCHAR(20) PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    email       TEXT,
    password    TEXT,
    phone_number TEXT,
    comments      VARCHAR(10),
    status      VARCHAR(20) DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'closed','leave'))
)
""")


# 4️⃣ Guest Faces Table (NEW)
cursor.execute("""
CREATE TABLE IF NOT EXISTS guest_faces (
    face_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id    VARCHAR(20) NOT NULL,
    encoding    TEXT NOT NULL,   -- JSON string of 128-dim face encoding
    added_on    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id)
)
""")


# 2️⃣ Attendance Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id    VARCHAR(20) NOT NULL,
    method      VARCHAR(20) CHECK(method IN ('RFID','Face','Manual')),
    device_id   VARCHAR(50),
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced      BOOLEAN DEFAULT 0,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id)
)
""")

# 3️⃣ Devices Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS devices (
    device_id   VARCHAR(50) PRIMARY KEY,
    type        VARCHAR(20) CHECK(type IN ('RFID','Camera')),
    location    VARCHAR(100)
)
""")

# 3️⃣ Devices Table
cursor.execute("""
CREATE TABLE beds (
    id      INTEGER       PRIMARY KEY AUTOINCREMENT,
    bed_id    VARCHAR (10)  NOT NULL,
    description VARCHAR (150) 
)
""")





# 3️⃣ guest_beds Table
cursor.execute("""
CREATE TABLE guest_beds (
    assignment_id INTEGER      PRIMARY KEY AUTOINCREMENT,
    guest_id      VARCHAR (20) NOT NULL,
    bed_id       VARCHAR (10) NOT NULL,
    assign_date   DATE         NOT NULL
                               DEFAULT (DATE('now') ),
    FOREIGN KEY (
        guest_id
    )
    REFERENCES guests (guest_id) ON UPDATE CASCADE
                                 ON DELETE CASCADE
)
""")

# 8️⃣ Authentication: Guest-based auth tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS guest_auth (
    guest_id    VARCHAR(20) PRIMARY KEY,
    email       TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    is_active   BOOLEAN DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE
)
""")

# 9️⃣ Guest Sessions table
cursor.execute("""
CREATE TABLE IF NOT EXISTS guest_sessions (
    session_id  TEXT PRIMARY KEY,
    guest_id    VARCHAR(20) NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at  TIMESTAMP,
    user_agent  TEXT,
    ip_address  TEXT,
    revoked     BOOLEAN DEFAULT 0,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE
)
""")

# 🔟 Guest Password resets table
cursor.execute("""
CREATE TABLE IF NOT EXISTS guest_password_resets (
    token       TEXT PRIMARY KEY,
    guest_id    VARCHAR(20) NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at  TIMESTAMP NOT NULL,
    used        BOOLEAN DEFAULT 0,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE
)
""")

# Indices
cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_guest_auth_email ON guest_auth(email)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_sessions_guest ON guest_sessions(guest_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_pwresets_guest ON guest_password_resets(guest_id)")

# 1️⃣1️⃣ Roles tables and seeding
cursor.execute("""
CREATE TABLE IF NOT EXISTS roles (
    role_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name  TEXT NOT NULL UNIQUE,
    priority   INTEGER NOT NULL
)
""")







# Seed default roles (priority: owner=1, residence=2, employee=3)
cursor.executemany(
    "INSERT OR IGNORE INTO roles (role_name, priority) VALUES (?, ?)",
    [
        ("residence", 1),
        ("employee", 2),
        ("owner", 3),
    ]
)








# 7️⃣ Insert Dummy Beds
beds = [
    ("001/1/1", "Floor 0 Flat 1 Room 1 Bed 1"),
    ("001/1/2", "Floor 0 Flat 1 Room 1 Bed 2"),
    ("001/1/3", "Floor 0 Flat 1 Room 1 Bed 3"),
    ("002/1/1", "Floor 0 Flat 2 Room 1 Bed 1"),
    ("002/1/2", "Floor 0 Flat 2 Room 1 Bed 2"),
    ("002/1/3", "Floor 0 Flat 2 Room 1 Bed 3"),
    ("002/1/2", "Floor 0 Flat 2 Room 2 Bed 1"),
    ("002/2/2", "Floor 0 Flat 2 Room 2 Bed 1"),
    ("002/2/2", "Floor 0 Flat 2 Room 2 Bed 2"),
    ("002/2/3", "Floor 0 Flat 2 Room 2 Bed 3"),
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


cursor.executemany(
    "INSERT OR IGNORE INTO beds (bed_id, description) VALUES (?, ?)",
    beds
)

# 5️⃣ Insert Dummy Guests
guests = [
("20250100000001","Rakshita","mock+8319940394@crib.in","8319940394"),
("20250100000002","Ramsha","9336980752@crib.in","9336980752"),
("20250100000003","Aqsa Amroha.","mock+9760775533@crib.in","9760775533"),
("20250100000004","Sana Ansari Bareilly.","9997255787@crib.in","9997255787"),
("20250100000005","Rukhsana","mock+9654088295@crib.in","9654088295"),
("20250100000006","Taezeen Hamid.","taezeen786+7006671809@gmail.com","7006671809"),
("20250100000007","Razbi Ara Kanpur","9792364990@crib.in","9792364990"),
("20250100000008","Sumaiya Khan Aligarh.","8171514921@crib.in","8171514921"),
("20250100000010","Sania Kausar","saniakausar032+9818867032@gmail.com","9818867032"),
("20250100000011","Aiysha Xi","mock+9906579310@crib.in","9906579310"),
("20250100000012","Darakhshan Zahid","darakhsahanji+9149569285@gmail.com","9149569285"),
("20250100000013","Alina Mustak Ix","mock+7889334398@crib.in","7889334398"),
("20250100000014","Kanza","7060666770@crib.in","7060666770"),
("20250100000015","Litpujam Gladia Lady.","7085600638@crib.in","7085600638"),
("20250100000016","Unzila Shams Uttrakhand","mock+7983660305@crib.in","7983660305"),
("20250100000017","Anam Mirza.","7302166766@crib.in","7302166766"),
("20250100000018","Kulsum Deoband","mock+9557009090@crib.in","9557009090"),
("20250100000019","Fariya Ali.","mock+7289831016@crib.in","7289831016"),
("20250100000020","Saujanya Sarkar","8777349575@crib.in","8777349575"),
("20250100000021","Roshni Bihar","8539084388@crib.in","8539084388"),
("20250100000022","Sara Khan Muradabad.","7906715399@crib.in","7906715399"),
("20250100000023","Sadiya.","8400285185@crib.in","8400285185"),
("20250100000024","Alruba Khan.","alrubakhan911gt3+7354338899@gmail.com","7354338899"),
("20250100000025","Sidra.","sidrasiddiqui952+7078481666@gmail.com","7078481666"),
("20250100000026","Fatima Durrani.","mock+6306103474@crib.in","6306103474"),
("20250100000027","Joya Yamuna Nagar.","mock+8295500787@crib.in","8295500787"),
("20250100000028","Eram Khan.","bhueramkhan+8418040470@gmail.com","8418040470"),
("20250100000029","Simrah Javed","simrahjaved611+8791891711@gmail.com","8791891711"),
("20250100000030","Shafiya Jammu.","mock+9103284409@crib.in","9103284409"),
("20250100000031","Bushra Jaipur.","9319058372@crib.in","9319058372"),
("20250100000032","Amisha Jha Vaishali","7856884933@crib.in","7856884933"),
("20250100000033","Saniya Siddiqui.","alinasiddiqui2007+7015665532@gmail.com","7015665532"),
("20250100000034","Tanuja Negi","8449694272@crib.in","8449694272"),
("20250100000035","Aysha Syed","9650068375@crib.in","9650068375"),
("20250100000036","Ambhi Singh.","ambhisingh111+7699559422@gmail.com","7699559422"),
("20250100000037","Shaista.","shaistaaju927+7352161466@gmail.com","7352161466"),
("20250100000038","Areeba Agra.","mock+8650690789@crib.in","8650690789"),
("20250100000039","Taqdeer Hussain.","taqdeer.504gc+7762990568@gmail.com","7762990568"),
("20250100000040","Aalia Harayana.","8814844786@crib.in","8814844786"),
("20250100000041","Iqra Fatehpur Tabassum.","mock+9667938102@crib.in","9667938102"),
("20250100000042","Zoha Shahzad","shahzadzoha60@gmail.com","#VALUE!"),
("20250100000043","Adeeba Shahzad","8077819424@crib.in","8077819424"),
("20250100000044","Umaima Fatima.","umaimaf676+7393022866@gmail.com","7393022866"),
("20250100000045","Sara Fatima.","mock+9170712038@crib.in","9170712038"),
("20250100000046","Saniya Haque.","mock+9128746730@crib.in","9128746730"),
("20250100000047","Sherish Naaz Muradabad.","9149257376@crib.in","9149257376"),
("20250100000048","Urooj Fatima","9719473122@crib.in","9719473122"),
("20250100000049","Saleena Waseem.","9760834337@crib.in","9760834337"),
("20250100000050","Sadaf Jamal.","gausiyasadaf2001+9335532134@gmail.com","9335532134"),
("20250100000051","Sunera","9818451599@crib.in","9818451599"),
("20250100000052","Faiza Srinagar.","6006414151@crib.in","6006414151"),
("20250100000053","Neha Khan","nk8474329+6388094396@gmail.com","6388094396"),
("20250100000055","Areeba Khan.","areebakhan62389+8006588406@gmail.com","8006588406"),
("20250100000056","Faizia Xi Shahjahanpur","mock+9451643726@crib.in","9451643726"),
("20250100000057","Sumra Sambul","mock+9631547599@crib.in","9631547599"),
("20250100000058","Shafia Bihar.","mock+9229214261@crib.in","9229214261"),
("20250100000060","Muskan Anjum.","mock+9142402767@crib.in","9142402767"),
("20250100000061","Ghausia.","ghausiaparween032+6290941265@gmail.com","6290941265"),
("20250100000062","Iqra Naaz Bijnor","mock+8979542119@crib.in","8979542119"),
("20250100000063","Iqra Khan Farukhabad.","iqrakhan8385+8009776840@gmail.com","8009776840"),
("20250100000064","Iqra Jaipur","8118859709@crib.in","8118859709"),
("20250100000066","Mrym.","mrymonshop+9897691116@gmail.com","9897691116"),
("20250100000067","Nida Farooqui.","nidafarooqui2626+9634941399@gmail.com","9634941399"),
("20250100000068","Aafnan Ashraf Patna.","mock+6201902265@crib.in","6201902265"),
("20250100000069","Nasra Afrien","roselucky1107+9369051398@gmail.com","9369051398"),
("20250100000070","Umam Samreen Hashmi.","mock+6306355591@crib.in","6306355591"),
("20250100000071","Surabhi Katariya","mock+8826513840@crib.in","8826513840"),
("20250100000072","Afsana Kosser","afsanakosser01+8492807440@gmail.com","8492807440"),
("20250100000073","Farheen Hak Jharkhand.","mock+7050563194@crib.in","7050563194"),
("20250100000074","Mufleha Khatoon,","muflehakhatoon95+8789706612@gmail.com","8789706612"),
("20250100000075","Alzia Lucknow","mock+6307894578@crib.in","6307894578"),
("20250100000076","Najiba Perween","najibaperween9+9934219896@gmail.com","9934219896"),
("20250100000077","Muskan Khatoon Coochbehar","mock+9064234514@crib.in","9064234514"),
("20250100000078","Aiman.","mock+7985348230@crib.in","7985348230"),
("20250100000079","Gazala Motihari.","mock+7870701853@crib.in","7870701853"),
("20250100000080","Isma Nanital","8899292240@crib.in","8899292240"),
("20250100000081","Aiman Naz Bihar","mock+8210731821@crib.in","8210731821"),
("20250100000082","Zohara Xith","mock+7858857798@crib.in","7858857798"),
("20250100000083","Wajiha Fatima.","wajihafatima2003+8102618006@gmail.com","8102618006")
]
# Insert sample data
cursor.executemany(
    "INSERT OR IGNORE INTO guests (guest_id, name, email, password, phone_number, comments, status) "
    "VALUES (?, ?, ?, 'Pass@123', ?, '', 'active')",
    guests
)
#cursor.executemany("INSERT OR IGNORE INTO guests VALUES (?,?,?,'Pass@123',?,'','Resident',1)", guests)




cursor.execute("""
CREATE TABLE IF NOT EXISTS guest_roles (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id   VARCHAR(20) NOT NULL UNIQUE,
    role_id    INTEGER NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE RESTRICT
)
""")

cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_roles_name ON roles(role_name)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_roles_guest ON guest_roles(guest_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_roles_role ON guest_roles(role_id)")

guest_roles=[
("20250105000001",1,"2025-10-02"),
("20250105000002",1,"2025-10-02"),
("20250105000003",1,"2025-10-02"),
("20250105000004",1,"2025-10-02"),
("20250105000005",1,"2025-10-02"),
("20250105000006",1,"2025-10-02"),
("20250105000007",1,"2025-10-02"),
("20250105000008",1,"2025-10-02"),
("20250105000010",1,"2025-10-02"),
("20250105000011",1,"2025-10-02"),
("20250105000012",1,"2025-10-02"),
("20250105000013",1,"2025-10-02"),
("20250105000014",1,"2025-10-02"),
("20250105000015",1,"2025-10-02"),
("20250105000016",1,"2025-10-02"),
("20250105000017",1,"2025-10-02"),
("20250105000018",1,"2025-10-02"),
("20250105000019",1,"2025-10-02"),
("20250105000020",1,"2025-10-02"),
("20250105000021",1,"2025-10-02"),
("20250105000022",1,"2025-10-02"),
("20250105000023",1,"2025-10-02"),
("20250105000024",1,"2025-10-02"),
("20250105000025",1,"2025-10-02"),
("20250105000026",1,"2025-10-02"),
("20250105000027",1,"2025-10-02"),
("20250105000028",1,"2025-10-02"),
("20250105000029",1,"2025-10-02"),
("20250105000030",1,"2025-10-02"),
("20250105000031",1,"2025-10-02"),
("20250105000032",1,"2025-10-02"),
("20250105000033",1,"2025-10-02"),
("20250105000034",1,"2025-10-02"),
("20250105000035",1,"2025-10-02"),
("20250105000036",1,"2025-10-02"),
("20250105000037",1,"2025-10-02"),
("20250105000038",1,"2025-10-02"),
("20250105000039",1,"2025-10-02"),
("20250105000040",1,"2025-10-02"),
("20250105000041",1,"2025-10-02"),
("20250105000042",1,"2025-10-02"),
("20250105000043",1,"2025-10-02"),
("20250105000044",1,"2025-10-02"),
("20250105000045",1,"2025-10-02"),
("20250105000046",1,"2025-10-02"),
("20250105000047",1,"2025-10-02"),
("20250105000048",1,"2025-10-02"),
("20250105000049",1,"2025-10-02"),
("20250105000050",1,"2025-10-02"),
("20250105000051",1,"2025-10-02"),
("20250105000052",1,"2025-10-02"),
("20250105000053",1,"2025-10-02"),
("20250105000055",1,"2025-10-02"),
("20250105000056",1,"2025-10-02"),
("20250105000057",1,"2025-10-02"),
("20250105000058",1,"2025-10-02"),
("20250105000060",1,"2025-10-02"),
("20250105000061",1,"2025-10-02"),
("20250105000062",1,"2025-10-02"),
("20250105000063",1,"2025-10-02"),
("20250105000064",1,"2025-10-02"),
("20250105000066",1,"2025-10-02"),
("20250105000067",1,"2025-10-02"),
("20250105000068",1,"2025-10-02"),
("20250105000069",1,"2025-10-02"),
("20250105000070",1,"2025-10-02"),
("20250105000071",1,"2025-10-02"),
("20250105000072",1,"2025-10-02"),
("20250105000073",1,"2025-10-02"),
("20250105000074",1,"2025-10-02"),
("20250105000075",1,"2025-10-02"),
("20250105000076",1,"2025-10-02"),
("20250105000077",1,"2025-10-02"),
("20250105000078",1,"2025-10-02"),
("20250105000079",1,"2025-10-02"),
("20250105000080",1,"2025-10-02"),
("20250105000081",1,"2025-10-02"),
("20250105000082",1,"2025-10-02"),
("20250105000083",1,"2025-10-02")
]


cursor.executemany(
    "INSERT OR IGNORE INTO guest_roles (guest_id, role_id,assigned_at) VALUES (?,?, ?)",
    guest_roles
)





# 6️⃣ Insert Dummy Devices
devices = [
    ("RFID01", "RFID", "Main Gate"),
    ("CAM01", "Camera", "Dining Hall"),
    ("EXIT_CAM", "Camera", "Out"),
    ("LIFT_CAM", "Camera", "In")        
]
cursor.executemany("INSERT OR IGNORE INTO devices VALUES (?,?,?)", devices)

# 7️⃣ Insert Dummy Attendance
attendance = [
    ("20250105000001", "RFID", "RFID01", "2025-09-16 20:15:00", 1),
    ("20250105000001", "Face", "CAM01", "2025-09-16 20:16:05", 1),
    ("20250210000002", "Manual", "ADMIN01", "2025-09-16 20:30:00", 0),
    ("20250301000003", "RFID", "RFID01", "2025-09-16 21:05:00", 1)
]
cursor.executemany("INSERT INTO attendance (guest_id, method, device_id, timestamp, synced) VALUES (?,?,?,?,?)", attendance)





# Insert dummy bed assignments
guest_beds = [
("20250105000001","002/2/1","2025-10-02"),
("20250105000002","001/2/1","2025-10-02"),
("20250105000003","002/1/1","2025-10-02"),
("20250105000004","103/1/1","2025-10-02"),
("20250105000005","103/2/1","2025-10-02"),
("20250105000006","104/1/1","2025-10-02"),
("20250105000007","104/2/1","2025-10-02"),
("20250105000008","203/1/1","2025-10-02"),
("20250105000010","204/1/1","2025-10-02"),
("20250105000011","204/1/2","2025-10-02"),
("20250105000012","204/2/1","2025-10-02"),
("20250105000013","204/2/2","2025-10-02"),
("20250105000014","204/2/3","2025-10-02"),
("20250105000015","303/1/1","2025-10-02"),
("20250105000016","303/1/2","2025-10-02"),
("20250105000017","303/2/1","2025-10-02"),
("20250105000018","303/2/2","2025-10-02"),
("20250105000019","304/1/1","2025-10-02"),
("20250105000020","304/1/2","2025-10-02"),
("20250105000021","304/2/1","2025-10-02"),
("20250105000022","304/2/2","2025-10-02"),
("20250105000023","401/1/1","2025-10-02"),
("20250105000024","401/1/2","2025-10-02"),
("20250105000025","401/1/3","2025-10-02"),
("20250105000026","401/2/1","2025-10-02"),
("20250105000027","401/2/2","2025-10-02"),
("20250105000028","401/2/3","2025-10-02"),
("20250105000029","402/1/1","2025-10-02"),
("20250105000030","402/1/2","2025-10-02"),
("20250105000031","402/1/3","2025-10-02"),
("20250105000032","402/2/1","2025-10-02"),
("20250105000033","402/2/2","2025-10-02"),
("20250105000034","402/2/3","2025-10-02"),
("20250105000035","403/1/1","2025-10-02"),
("20250105000036","403/1/2","2025-10-02"),
("20250105000037","403/2/1","2025-10-02"),
("20250105000038","403/2/2","2025-10-02"),
("20250105000039","404/1/1","2025-10-02"),
("20250105000040","404/1/2","2025-10-02"),
("20250105000041","404/2/1","2025-10-02"),
("20250105000042","404/2/2","2025-10-02"),
("20250105000043","404/2/3","2025-10-02"),
("20250105000044","501/1/1","2025-10-02"),
("20250105000045","501/1/2","2025-10-02"),
("20250105000046","501/1/3","2025-10-02"),
("20250105000047","501/2/1","2025-10-02"),
("20250105000048","501/2/2","2025-10-02"),
("20250105000049","501/2/3","2025-10-02"),
("20250105000050","502/1/1","2025-10-02"),
("20250105000051","502/1/2","2025-10-02"),
("20250105000052","502/1/3","2025-10-02"),
("20250105000053","502/2/1","2025-10-02"),
("20250105000055","502/2/3","2025-10-02"),
("20250105000056","503/1/1","2025-10-02"),
("20250105000057","503/1/2","2025-10-02"),
("20250105000058","503/2/1","2025-10-02"),
("20250105000060","504/1/1","2025-10-02"),
("20250105000061","504/1/2","2025-10-02"),
("20250105000062","504/2/1","2025-10-02"),
("20250105000063","504/2/2","2025-10-02"),
("20250105000064","504/2/3","2025-10-02"),
("20250105000066","303/2/3","2025-10-02"),
("20250105000067","403/2/3","2025-10-02"),
("20250105000068","503/2/3","2025-10-02"),
("20250105000069","002/2/2","2025-10-02"),
("20250105000070","002/2/3","2025-10-02"),
("20250105000071","002/1/2","2025-10-02"),
("20250105000072","002/1/3","2025-10-02"),
("20250105000073","001/2/2","2025-10-02"),
("20250105000074","001/2/3","2025-10-02"),
("20250105000075","103/1/2","2025-10-02"),
("20250105000076","103/2/2","2025-10-02"),
("20250105000077","103/2/3","2025-10-02"),
("20250105000078","104/2/2","2025-10-02"),
("20250105000079","104/2/3","2025-10-02"),
("20250105000080","203/2/2","2025-10-02"),
("20250105000081","203/2/3","2025-10-02"),
("20250105000082","104/1/2","2025-10-02"),
("20250105000083","203/1/2","2025-10-02")
]
cursor.executemany(
    "INSERT OR IGNORE INTO guest_beds (guest_id, bed_id, assign_date) VALUES (?, ?, ?)",
    guest_beds
)



cursor.execute('''CREATE TABLE guest_metadata (
    meta_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id    VARCHAR(20) NOT NULL,
    name        VARCHAR(20) NOT NULL,
    description VARCHAR(150),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guest_id) REFERENCES guests(guest_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
)''')

guest_metadata = [
("20250105000001","registered","002/2/1","2025-10-02"),
("20250105000002","registered","001/2/1","2025-10-02"),
("20250105000003","registered","002/1/1","2025-10-02"),
("20250105000004","registered","103/1/1","2025-10-02"),
("20250105000005","registered","103/2/1","2025-10-02"),
("20250105000006","registered","104/1/1","2025-10-02"),
("20250105000007","registered","104/2/1","2025-10-02"),
("20250105000008","registered","203/1/1","2025-10-02"),
("20250105000010","registered","204/1/1","2025-10-02"),
("20250105000011","registered","204/1/2","2025-10-02"),
("20250105000012","registered","204/2/1","2025-10-02"),
("20250105000013","registered","204/2/2","2025-10-02"),
("20250105000014","registered","204/2/3","2025-10-02"),
("20250105000015","registered","303/1/1","2025-10-02"),
("20250105000016","registered","303/1/2","2025-10-02"),
("20250105000017","registered","303/2/1","2025-10-02"),
("20250105000018","registered","303/2/2","2025-10-02"),
("20250105000019","registered","304/1/1","2025-10-02"),
("20250105000020","registered","304/1/2","2025-10-02"),
("20250105000021","registered","304/2/1","2025-10-02"),
("20250105000022","registered","304/2/2","2025-10-02"),
("20250105000023","registered","401/1/1","2025-10-02"),
("20250105000024","registered","401/1/2","2025-10-02"),
("20250105000025","registered","401/1/3","2025-10-02"),
("20250105000026","registered","401/2/1","2025-10-02"),
("20250105000027","registered","401/2/2","2025-10-02"),
("20250105000028","registered","401/2/3","2025-10-02"),
("20250105000029","registered","402/1/1","2025-10-02"),
("20250105000030","registered","402/1/2","2025-10-02"),
("20250105000031","registered","402/1/3","2025-10-02"),
("20250105000032","registered","402/2/1","2025-10-02"),
("20250105000033","registered","402/2/2","2025-10-02"),
("20250105000034","registered","402/2/3","2025-10-02"),
("20250105000035","registered","403/1/1","2025-10-02"),
("20250105000036","registered","403/1/2","2025-10-02"),
("20250105000037","registered","403/2/1","2025-10-02"),
("20250105000038","registered","403/2/2","2025-10-02"),
("20250105000039","registered","404/1/1","2025-10-02"),
("20250105000040","registered","404/1/2","2025-10-02"),
("20250105000041","registered","404/2/1","2025-10-02"),
("20250105000042","registered","404/2/2","2025-10-02"),
("20250105000043","registered","404/2/3","2025-10-02"),
("20250105000044","registered","501/1/1","2025-10-02"),
("20250105000045","registered","501/1/2","2025-10-02"),
("20250105000046","registered","501/1/3","2025-10-02"),
("20250105000047","registered","501/2/1","2025-10-02"),
("20250105000048","registered","501/2/2","2025-10-02"),
("20250105000049","registered","501/2/3","2025-10-02"),
("20250105000050","registered","502/1/1","2025-10-02"),
("20250105000051","registered","502/1/2","2025-10-02"),
("20250105000052","registered","502/1/3","2025-10-02"),
("20250105000053","registered","502/2/1","2025-10-02"),
("20250105000055","registered","502/2/3","2025-10-02"),
("20250105000056","registered","503/1/1","2025-10-02"),
("20250105000057","registered","503/1/2","2025-10-02"),
("20250105000058","registered","503/2/1","2025-10-02"),
("20250105000060","registered","504/1/1","2025-10-02"),
("20250105000061","registered","504/1/2","2025-10-02"),
("20250105000062","registered","504/2/1","2025-10-02"),
("20250105000063","registered","504/2/2","2025-10-02"),
("20250105000064","registered","504/2/3","2025-10-02"),
("20250105000066","registered","303/2/3","2025-10-02"),
("20250105000067","registered","403/2/3","2025-10-02"),
("20250105000068","registered","503/2/3","2025-10-02"),
("20250105000069","registered","002/2/2","2025-10-02"),
("20250105000070","registered","002/2/3","2025-10-02"),
("20250105000071","registered","002/1/2","2025-10-02"),
("20250105000072","registered","002/1/3","2025-10-02"),
("20250105000073","registered","001/2/2","2025-10-02"),
("20250105000074","registered","001/2/3","2025-10-02"),
("20250105000075","registered","103/1/2","2025-10-02"),
("20250105000076","registered","103/2/2","2025-10-02"),
("20250105000077","registered","103/2/3","2025-10-02"),
("20250105000078","registered","104/2/2","2025-10-02"),
("20250105000079","registered","104/2/3","2025-10-02"),
("20250105000080","registered","203/2/2","2025-10-02"),
("20250105000081","registered","203/2/3","2025-10-02"),
("20250105000083","registered","203/1/2","2025-10-02"),
("20250105000082","registered","104/1/2","2025-10-02"),
("20250105000001","bed assigned","002/2/1","2025-10-02"),
("20250105000002","bed assigned","001/2/1","2025-10-02"),
("20250105000003","bed assigned","002/1/1","2025-10-02"),
("20250105000004","bed assigned","103/1/1","2025-10-02"),
("20250105000005","bed assigned","103/2/1","2025-10-02"),
("20250105000006","bed assigned","104/1/1","2025-10-02"),
("20250105000007","bed assigned","104/2/1","2025-10-02"),
("20250105000008","bed assigned","203/1/1","2025-10-02"),
("20250105000010","bed assigned","204/1/1","2025-10-02"),
("20250105000011","bed assigned","204/1/2","2025-10-02"),
("20250105000012","bed assigned","204/2/1","2025-10-02"),
("20250105000013","bed assigned","204/2/2","2025-10-02"),
("20250105000014","bed assigned","204/2/3","2025-10-02"),
("20250105000015","bed assigned","303/1/1","2025-10-02"),
("20250105000016","bed assigned","303/1/2","2025-10-02"),
("20250105000017","bed assigned","303/2/1","2025-10-02"),
("20250105000018","bed assigned","303/2/2","2025-10-02"),
("20250105000019","bed assigned","304/1/1","2025-10-02"),
("20250105000020","bed assigned","304/1/2","2025-10-02"),
("20250105000021","bed assigned","304/2/1","2025-10-02"),
("20250105000022","bed assigned","304/2/2","2025-10-02"),
("20250105000023","bed assigned","401/1/1","2025-10-02"),
("20250105000024","bed assigned","401/1/2","2025-10-02"),
("20250105000025","bed assigned","401/1/3","2025-10-02"),
("20250105000026","bed assigned","401/2/1","2025-10-02"),
("20250105000027","bed assigned","401/2/2","2025-10-02"),
("20250105000028","bed assigned","401/2/3","2025-10-02"),
("20250105000029","bed assigned","402/1/1","2025-10-02"),
("20250105000030","bed assigned","402/1/2","2025-10-02"),
("20250105000031","bed assigned","402/1/3","2025-10-02"),
("20250105000032","bed assigned","402/2/1","2025-10-02"),
("20250105000033","bed assigned","402/2/2","2025-10-02"),
("20250105000034","bed assigned","402/2/3","2025-10-02"),
("20250105000035","bed assigned","403/1/1","2025-10-02"),
("20250105000036","bed assigned","403/1/2","2025-10-02"),
("20250105000037","bed assigned","403/2/1","2025-10-02"),
("20250105000038","bed assigned","403/2/2","2025-10-02"),
("20250105000039","bed assigned","404/1/1","2025-10-02"),
("20250105000040","bed assigned","404/1/2","2025-10-02"),
("20250105000041","bed assigned","404/2/1","2025-10-02"),
("20250105000042","bed assigned","404/2/2","2025-10-02"),
("20250105000043","bed assigned","404/2/3","2025-10-02"),
("20250105000044","bed assigned","501/1/1","2025-10-02"),
("20250105000045","bed assigned","501/1/2","2025-10-02"),
("20250105000046","bed assigned","501/1/3","2025-10-02"),
("20250105000047","bed assigned","501/2/1","2025-10-02"),
("20250105000048","bed assigned","501/2/2","2025-10-02"),
("20250105000049","bed assigned","501/2/3","2025-10-02"),
("20250105000050","bed assigned","502/1/1","2025-10-02"),
("20250105000051","bed assigned","502/1/2","2025-10-02"),
("20250105000052","bed assigned","502/1/3","2025-10-02"),
("20250105000053","bed assigned","502/2/1","2025-10-02"),
("20250105000055","bed assigned","502/2/3","2025-10-02"),
("20250105000056","bed assigned","503/1/1","2025-10-02"),
("20250105000057","bed assigned","503/1/2","2025-10-02"),
("20250105000058","bed assigned","503/2/1","2025-10-02"),
("20250105000060","bed assigned","504/1/1","2025-10-02"),
("20250105000061","bed assigned","504/1/2","2025-10-02"),
("20250105000062","bed assigned","504/2/1","2025-10-02"),
("20250105000063","bed assigned","504/2/2","2025-10-02"),
("20250105000064","bed assigned","504/2/3","2025-10-02"),
("20250105000066","bed assigned","303/2/3","2025-10-02"),
("20250105000067","bed assigned","403/2/3","2025-10-02"),
("20250105000068","bed assigned","503/2/3","2025-10-02"),
("20250105000069","bed assigned","002/2/2","2025-10-02"),
("20250105000070","bed assigned","002/2/3","2025-10-02"),
("20250105000071","bed assigned","002/1/2","2025-10-02"),
("20250105000072","bed assigned","002/1/3","2025-10-02"),
("20250105000073","bed assigned","001/2/2","2025-10-02"),
("20250105000074","bed assigned","001/2/3","2025-10-02"),
("20250105000075","bed assigned","103/1/2","2025-10-02"),
("20250105000076","bed assigned","103/2/2","2025-10-02"),
("20250105000077","bed assigned","103/2/3","2025-10-02"),
("20250105000078","bed assigned","104/2/2","2025-10-02"),
("20250105000079","bed assigned","104/2/3","2025-10-02"),
("20250105000080","bed assigned","203/2/2","2025-10-02"),
("20250105000081","bed assigned","203/2/3","2025-10-02"),
("20250105000082","bed assigned","104/1/2","2025-10-02"),
("20250105000083","bed assigned","203/1/2","2025-10-02")
]

cursor.executemany(
    "INSERT OR IGNORE INTO guest_metadata (guest_id, name, description,created_at) VALUES (?, ?,?, ?)",
    guest_metadata
)





cursor.execute('''CREATE TABLE auth_sessions (
        session_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        user_agent TEXT,
        ip_address TEXT,
        revoked INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )''')
#cursor.execute('''CREATE TABLE guest_auth (guest_id VARCHAR (20) PRIMARY KEY, email TEXT UNIQUE, password_hash TEXT NOT NULL, is_active INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (guest_id) REFERENCES guests (guest_id) ON DELETE CASCADE)''')
#cursor.execute('''CREATE TABLE guest_sessions (session_id TEXT PRIMARY KEY, guest_id VARCHAR (20) NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP, user_agent TEXT, ip_address TEXT, revoked INTEGER DEFAULT 0, FOREIGN KEY (guest_id) REFERENCES guests (guest_id) ON DELETE CASCADE)''')





def generate_attendance_records(start_date: str, end_date: str, total_records: int = 3000):
    """
    Generate random attendance data between start_date and end_date.
    Example: start_date='2025-01-01', end_date='2025-01-30'
    """


    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    delta_days = (end_dt - start_dt).days
    records = []

    for _ in range(total_records):
        # Random guest_id in given range
        guest_id = f"202501{random.randint(1,83):08d}"

        # Random day within range
        random_day = start_dt + timedelta(days=random.randint(0, delta_days))
        # Random time in the day
        random_time = timedelta(seconds=random.randint(0, 86399))
        timestamp = random_day + random_time
        hour = timestamp.hour

        # Decide device_id based on time logic
        if 18 <= hour <= 23:
            # 6 PM – 11 PM → mostly LIFT_CAM
            device_id = "LIFT_CAM" if random.random() < 0.95 else "EXIT_CAM"
        elif 6 <= hour < 18:
            # 6 AM – 6 PM → 50% EXIT_CAM
            device_id = "EXIT_CAM" if random.random() < 0.5 else "LIFT_CAM"
        else:
            # Late night or early morning (after 11 PM)
            # Small % appear — randomly assign
            device_id = random.choice(["EXIT_CAM", "LIFT_CAM"])

        records.append((guest_id, "Face", device_id, timestamp.strftime("%Y-%m-%d %H:%M:%S"), 0))
    #cursor.execute("DELETE FROM attendance;")
    cursor.executemany(
        "INSERT INTO attendance (guest_id, method, device_id, timestamp, synced) VALUES (?,?,?,?,?)",
        records
    )


    print(f"✅ Inserted {total_records} random attendance records from {start_date} to {end_date}.")



########################################
generate_attendance_records(start_date="2025-09-01", end_date="2025-10-27", total_records=10000);
#######################################3


# 8️⃣ Insert Dummy Guest Faces (fake encodings for demo)
# Normally you’d store json.dumps(face_encoding.tolist())
# ----------------------------
# Known faces folder
# ----------------------------
BASE_DIR = Path(__file__).resolve().parent
KNOWN_DIR = BASE_DIR / "..//..//../images"   # Folder: images/Alice/*.jpg, images/Bob/*.jpg

# ----------------------------
# Loop through folders
# ----------------------------
for person_dir in KNOWN_DIR.iterdir():
    if not person_dir.is_dir():
        continue

    guest_id = person_dir.name  # folder name = guest_id
    print(f"[INFO] Processing (guest_id)...")

    for img_path in person_dir.glob("*.jpg"):
        # Load image
        img = face_recognition.load_image_file(str(img_path))
        encs = face_recognition.face_encodings(img)

        if len(encs) == 0:
            print(f"[WARNING] No face found in {img_path}")
            continue

        encoding = encs[0]
        encoding_json = json.dumps(encoding.tolist())  # save as JSON string

        # Insert into DB
        cursor.execute(
            "INSERT INTO guest_faces (guest_id, encoding) VALUES (?, ?)",
            (guest_id, encoding_json)
        )


# Commit & Close
conn.commit()
conn.close()

print("✅ WhiteHouse.db created/updated with guests, attendance, devices, guest_faces, guest_auth, guest_sessions, guest_password_resets, roles, guest_roles tables!")


