from fastapi import FastAPI
import threading
import logging
from .database import engine, Base
from .consumers import run_consumer, process_examiner_event, process_tutor_event
from .config import settings
from .aggregator import start_scheduler
from .routers import insights, activity
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from src.database import SessionLocal
from src.models import DailyActivity, WeeklyActivity
from datetime import datetime, timedelta, date
from sqlalchemy import func
import redis

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tutor_insights")

# Create Tables (for now, in prod use migration)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tutor Insights Service")

# CORS for direct access if needed (proxy is primary)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173", "http://localhost:4501", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(insights.router)
app.include_router(activity.router, prefix="/api/v1")

# Background Jobs for Activity
def sync_daily_activity():
    """
    Syncs daily activity from Redis to Database
    """
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        # Scan for keys: activity:{student_id}:{date}
        # We process keys from yesterday to avoid race conditions with ongoing heartbeats,
        # or process current day and update DB upsert style.
        # Strategy: Process ALL keys, update DB, then maybe delete old keys or rely on TTL.
        # Better: Daily job processes 'yesterday' data fully and 'today' partial.
        
        # Let's iterate all activity keys
        cursor = '0'
        while cursor != 0:
            cursor, keys = redis_client.scan(cursor=cursor, match="activity:*", count=100)
            if keys:
                db = SessionLocal()
                try:
                    for key in keys:
                        # key format: activity:student_id:subject:YYYY-MM-DD
                        parts = key.split(":")
                        student_id = parts[1]
                        subject = parts[2]
                        date_str = parts[3]
                        
                        try:
                            activity_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                            seconds = int(redis_client.get(key) or 0)
                            
                            # Upsert into DailyActivity
                            existing = db.query(DailyActivity).filter(
                                DailyActivity.student_id == student_id,
                                DailyActivity.subject == subject,
                                DailyActivity.date == activity_date
                            ).first()
                            
                            if existing:
                                existing.seconds_active = seconds
                            else:
                                new_activity = DailyActivity(
                                    student_id=student_id, 
                                    subject=subject,
                                    date=activity_date, 
                                    seconds_active=seconds
                                )
                                db.add(new_activity)
                        except ValueError:
                            logger.error(f"Invalid date in key: {key}")
                            continue
                    db.commit()
                except Exception as e:
                    logger.error(f"Error syncing daily activity: {e}")
                    db.rollback()
                finally:
                    db.close()
            if cursor == 0:
                break
                
        logger.info("Daily activity sync completed")
    except Exception as e:
        logger.error(f"Failed to run daily activity sync: {e}")

def aggregate_weekly_activity():
    """
    Aggregates DailyActivity into WeeklyActivity.
    Processes both the previous week (to finalize) and current week.
    Deletes DailyActivity data older than the current week.
    """
    db = SessionLocal()
    try:
        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())
        last_week_start = current_week_start - timedelta(days=7)
        
        # Helper to aggregate a specific week
        def aggregate_week(start_date):
            end_date = start_date + timedelta(days=6)
            
            # Select distinct (student_id, subject) active this week
            records = db.query(DailyActivity.student_id, DailyActivity.subject).filter(
                DailyActivity.date >= start_date,
                DailyActivity.date <= end_date
            ).distinct().all()
            
            for student_id, subject in records:
                total_seconds = db.query(func.sum(DailyActivity.seconds_active)).filter(
                    DailyActivity.student_id == student_id,
                    DailyActivity.subject == subject,
                    DailyActivity.date >= start_date,
                    DailyActivity.date <= end_date
                ).scalar() or 0
                
                # Upsert WeeklyActivity
                existing = db.query(WeeklyActivity).filter(
                    WeeklyActivity.student_id == student_id,
                    WeeklyActivity.subject == subject,
                    WeeklyActivity.week_start == start_date
                ).first()
                
                if existing:
                    existing.seconds_active = total_seconds
                    existing.week_end = end_date
                else:
                    new_weekly = WeeklyActivity(
                        student_id=student_id,
                        subject=subject,
                        week_start=start_date,
                        week_end=end_date,
                        seconds_active=total_seconds
                    )
                    db.add(new_weekly)
        
        # Aggregate Last Week (Finalize)
        aggregate_week(last_week_start)
        
        # Aggregate Current Week (Live update)
        aggregate_week(current_week_start)
        
        # Delete DailyActivity older than current week start
        # This keeps the current week's daily data for ongoing aggregation,
        # but cleans up everything from previous weeks as they are now fully aggregated.
        db.query(DailyActivity).filter(DailyActivity.date < current_week_start).delete()
        
        db.commit()
        logger.info("Weekly activity aggregation and cleanup completed")
        
    except Exception as e:
        logger.error(f"Error aggregating weekly activity: {e}")
        db.rollback()
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    # Start Examiner Consumer
    if settings.EXAMINER_QUEUE_URL:
        t1 = threading.Thread(
            target=run_consumer, 
            args=(settings.EXAMINER_QUEUE_URL, process_examiner_event, "tutor_examiner_queue"),
            daemon=True
        )
        t1.start()

    # Start Tutor Consumer
    if settings.TUTOR_QUEUE_URL:
        t2 = threading.Thread(
            target=run_consumer, 
            args=(settings.TUTOR_QUEUE_URL, process_tutor_event, "tutor_account_queue"),
            daemon=True
        )
        t2.start()

    # Start Aggregator Scheduler (existing)
    start_scheduler()
    
    # Internal Scheduler for Activity
    scheduler = BackgroundScheduler()
    # Sync Redis to DB every 10 minutes (or hour)
    scheduler.add_job(sync_daily_activity, 'interval', minutes=10)
    # Aggregate weekly stats daily at midnight
    scheduler.add_job(aggregate_weekly_activity, 'cron', hour=0, minute=5)
    scheduler.start()

@app.get("/health")
def health_check():
    return {"status": "ok"}
