import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

from typing import List
from models.reports_model import ReportRequest, ReportResponse
import threading
import csv
import sqlite3,os
from dotenv import load_dotenv, find_dotenv
from utilities.environment_variables import load_environment



#load_environment(env_path);

load_environment("./../data/.env.webapp")


#load_dotenv(dotenv_path="./data/.env.webapp")
#load_dotenv(find_dotenv())
DB_PATH=os.getenv("DB_PATH")
if DB_PATH is None: DB_PATH = "./../data/WhiteHouse.db"
REPORTS_DIR =os.getenv("reports")  # Folder where report files are saved
if REPORTS_DIR is None: REPORTS_DIR = "reports"

# Ensure reports directory exists
os.makedirs(REPORTS_DIR, exist_ok=True)


def generate_report_async(from_date: str, to_date: str,emails :List[str]):
    """Start background thread to process guest video and extract encodings."""
    thread = threading.Thread(target=generate_report, args=(from_date, to_date,emails))
    thread.daemon = True
    thread.start()



def generate_report(from_date: str, to_date: str,emails: List[str]):
    """
    Example: Generate a dummy text report.
    You can replace this logic with DB query/export (attendance, etc.).
    """

    filepath= generate_attendance_report(from_date,to_date)
    send_email_with_attachment(emails, filepath)
    return filepath


def send_email_with_attachment(to_emails: List[str], file_path: str):
    """
    write.to.whitehouse@gmail.com: khmr nmnc aueg qejr
    Send the generated report via Gmail SMTP.
    You need to enable 'App Password' in Gmail account settings.
    """
    
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")


    msg = EmailMessage()
    msg["Subject"] = "WH Attendance Report"
    msg["From"] = EMAIL_USER
    msg["To"] = ", ".join(to_emails)
    msg.set_content("Please find the attached report.")

    # Attach the report file
    with open(file_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="text",
            subtype="plain",
            filename=os.path.basename(file_path)
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

    print(f"[EMAIL] Report sent to {to_emails}")


def process_report_request(report: ReportRequest) -> ReportResponse:
    """
    Generate + Email the report.
    """

        # ✅ Start background processing
    

    generate_report_async(report.from_date, report.to_date,report.emails)
    #send_email_with_attachment(report.emails, report_path)
    return ReportResponse(message="Report generated and sent successfully!")






def generate_attendance_report(from_date: str, to_date: str):
    """
    Generate attendance report between given date range and save to a CSV file.

    Args:
        from_date (str): Start date in 'YYYY-MM-DD' format
        to_date (str): End date in 'YYYY-MM-DD' format
        reports_dir (str): Folder where report file will be saved
        db_path (str): Path to SQLite database (default: ./data/WhiteHouse.db)
    """

    # Create filename and path
    filename = f"report_{from_date}_to_{to_date}.csv"
    filepath = os.path.join(REPORTS_DIR, filename)
    # Connect to DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # SQL query with date filtering
    cursor.execute("""
        SELECT 
            g.name,
            g.bed_no,
            g.guest_id,
            a.method,
            a.device_id,
            a.timestamp
        FROM attendance AS a
        JOIN guests AS g ON a.guest_id = g.guest_id
        WHERE date(a.timestamp) BETWEEN ? AND ?
        ORDER BY a.timestamp DESC
    """, (from_date, to_date))

    rows = cursor.fetchall()

    # Write to CSV
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["S.No", "Name", "Bed No", "Guest ID", "Method", "Device ID", "Timestamp"])
        for i, row in enumerate(rows, start=1):
            writer.writerow([i] + list(row))

    conn.close()

    print(f"✅ Report generated successfully: {filepath}")
    return filepath






def guest_presence_report(till_date: str):
    """
    Generate guest presence/missing report between (till_date - 48 hrs) and till_date.
    Example: /reports/guest_presence?till_date=2025-10-02
    """

    # Parse and calculate date range
    till_dt = datetime.strptime(till_date, "%Y-%m-%d")
    start_dt = till_dt - timedelta(hours=48)
    start_str = start_dt.strftime("%Y-%m-%d 00:00:00")
    end_str = till_dt.strftime("%Y-%m-%d 23:59:59")

    query = f"""
    WITH latest_activity AS (
        SELECT 
            a1.guest_id,
            a1.device_id AS latest_device,
            a1.timestamp AS latest_time
        FROM attendance a1
        INNER JOIN (
            SELECT 
                guest_id,
                MAX(timestamp) AS latest_time
            FROM attendance
            WHERE timestamp BETWEEN '{start_str}' AND '{end_str}'
            GROUP BY guest_id
        ) a2 
        ON a1.guest_id = a2.guest_id AND a1.timestamp = a2.latest_time
    )
    SELECT 
        g.guest_id,
        g.name,
        b.bed_id,
        CASE 
            WHEN la.latest_device = 'LIFT_CAM' THEN 'present'
            WHEN la.latest_device = 'EXIT_CAM' THEN 'not present'
            ELSE 'unknown'
        END AS current_status,
        la.latest_time AS latest_entry_time,
        ROUND(
            (JULIANDAY('{end_str}') - JULIANDAY(la.latest_time)) * 24,
            2
        ) AS missing_hrs
    FROM guests AS g
    LEFT JOIN guest_beds AS gb ON g.guest_id = gb.guest_id
    LEFT JOIN beds AS b ON gb.bed_id = b.bed_id
    LEFT JOIN latest_activity AS la ON g.guest_id = la.guest_id
    ORDER BY current_status, missing_hrs DESC;
    """

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    # Convert to list of dicts
    report = [dict(zip(columns, row)) for row in rows]

    conn.close()

    return {
        "status": "success",
        "till_date": till_date,
        "from_date": start_dt.strftime("%Y-%m-%d"),
        "count": len(report),
        "data": report
    }
