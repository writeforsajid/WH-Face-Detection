from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
from db.database import get_connection
from datetime import date
# This is your task
from Jobs.rent_due_job  import RentDueJob
from services.rent_due_email import RentDueEmailService
from services.payment_email import PaymentEmailService


print("Job completed.")

scheduler = AsyncIOScheduler()

def start_scheduler():
    # 00:00 → create dues
    scheduler.add_job(
        RentDueJob.run,
        CronTrigger(hour=0, minute=0),
        id="rent_due_insert",
        replace_existing=True
    )

    # 00:05 → send emails
    scheduler.add_job(
        RentDueEmailService.send,
        CronTrigger(hour=0, minute=5),
        id="rent_due_email",
        replace_existing=True
    )

    scheduler.start()
