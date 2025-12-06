from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
from db.database import get_connection
# This is your task
async def insert_midnight_data():
    print("Running midnight job...")
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO appconfig (name, description)
            VALUES (?, ?)
        """, ("TEST", "Midnight job insertion"))

        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()

    print("Job completed.")

scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(
        insert_midnight_data,
        CronTrigger(hour=0, minute=0),  # Runs every day at 00:00
        id="midnight_job",
        replace_existing=True
    )
    scheduler.start()
