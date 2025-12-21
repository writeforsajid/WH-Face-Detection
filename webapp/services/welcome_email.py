from utilities.email_service import send_email


class WelcomeEmailService:

    @staticmethod
    async def send(guest_id, name, email):
        if not email:
            return

        await send_email(
            to=[email],
            subject="Welcome to WH PG",
            template_name="welcome.html",
            template_data={
                "name": name,
                "company_name": "WH PG",
                "contact": "+91-XXXXXXXXXX"
            },
            guest_id=guest_id
        )
