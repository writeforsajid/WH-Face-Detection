from utilities.email_service import send_email
from services.log_service import add_guest_metadata
from datetime import datetime
from db.database import get_connection

class WelcomeEmailService:

    @staticmethod
    async def send(guest_id, name, email):
        if not email:
            return
        # -------------------------
        # 1️⃣ Fetch email setting
        # -------------------------
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT description FROM appconfig WHERE name = ?",
            ("EMAIL_NOTIFICATION",)
        )
        row = cur.fetchone()
        conn.close()
        email_enabled=True
        if row:
            email_enabled = row and row[0].lower() == "on"
        

        # -------------------------
        # 2️⃣ Send email ONLY if enabled
        # -------------------------
        if email_enabled and email:
            await send_email(
                to=[email],
                subject="Test Email: Please ignore",
                template_name="welcome.html",
                template_data={
                    "name": name,
                    "company_name": "WH PG",
                    "contact": "+91-XXXXXXXXXX"
                },
                guest_id=guest_id
            )

        # -------------------------
        # 3️⃣ ALWAYS save metadata
        # -------------------------
        meta = {
            "guest_id": guest_id,
            "name": "email_welcome",
            "description": "welcome.html",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        add_guest_metadata(meta)
