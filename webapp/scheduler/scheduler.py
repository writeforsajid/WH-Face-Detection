from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
import asyncio

from Jobs.rent_due_job import RentDueJob
from services.rent_due_email import RentDueEmailService
from services.payment_email import PaymentEmailService

# ✅ Executors (prevents blocking)
executors = {
    "default": ThreadPoolExecutor(max_workers=10)
}

# ✅ Job defaults (VERY IMPORTANT)
job_defaults = {
    "coalesce": True,      # merge missed runs into one
    "max_instances": 1    # never overlap same job
}

# ✅ Use IST explicitly
scheduler = AsyncIOScheduler(
    executors=executors,
    job_defaults=job_defaults,
    timezone="Asia/Kolkata"
)


def start_scheduler():
    # 🕛 00:00 → create rent dues
    scheduler.add_job(
        RentDueJob.run,
        trigger=CronTrigger(hour=0, minute=0),
        id="rent_due_insert",
        replace_existing=True,
        misfire_grace_time=600  # 10 minutes
    )

    # 🕛 00:05 → send due emails
    scheduler.add_job(
        RentDueEmailService.send,
        trigger=CronTrigger(hour=0, minute=5),
        id="rent_due_email",
        replace_existing=True,
        misfire_grace_time=600
    )

    scheduler.start()
