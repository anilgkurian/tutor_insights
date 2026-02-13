from fastapi import FastAPI
import threading
import logging
from .database import engine, Base
from .consumers import run_consumer, process_examiner_event, process_tutor_event
from .config import settings
from .aggregator import start_scheduler
from .routers import insights, activity, feedback
from .services.feedback_service import FeedbackService
import asyncio
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
# Base.metadata.create_all(bind=engine)

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
app.include_router(feedback.router, prefix="/api/v1")

# Background Jobs for Activity
def sync_daily_activity():
    """
    Syncs daily activity from Redis to Database
    """
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )
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
    Uses batch processing for efficiency and resilience.
    """
    batch_size = 100
    
    def aggregate_week(start_date, is_cleanup=False):
        # We use a new session per batch or keep one? 
        # Better to keep one session but commit incrementally.
        db = SessionLocal()
        try:
            end_date = start_date + timedelta(days=6)
            
            # Query sums directly using GROUP BY
            # Use yield_per if supported by driver, or just manual paging if we had an ID. 
            # Since we group by student/subject, standard paging is tricky without an order.
            # For simplicity with SQLAlchemy and potential driver limitations on yield_per with group_by,
            # we can just fetch all (if fits in memory) or use a windowed query if strictly needed.
            # But the user asked for "batches". Python-side batching of the upserts is the main gain here 
            # if we assume the aggregate query itself isn't the bottleneck (it usually converts N rows to M rows).
            # If the aggregate query is too heavy, we'd need to partition by student_id range.
            
            # Let's try to process the RESULT of the aggregation in batches.
            query = db.query(
                DailyActivity.student_id, 
                DailyActivity.subject,
                func.sum(DailyActivity.seconds_active).label("total_seconds")
            ).filter(
                DailyActivity.date >= start_date,
                DailyActivity.date <= end_date
            ).group_by(
                DailyActivity.student_id, 
                DailyActivity.subject
            )
            
            results = query.all() # Fetching aggregated results.
            
            # Process in batches
            for i in range(0, len(results), batch_size):
                batch = results[i:i + batch_size]
                
                for student_id, subject, total_seconds in batch:
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
                            seconds_active=total_seconds or 0
                        )
                        db.add(new_weekly)
                
                # Commit batch
                try:
                    db.commit()
                except Exception as e:
                    logger.error(f"Error committing batch for {start_date}: {e}")
                    db.rollback()
                    
        except Exception as e:
            logger.error(f"Error aggregating week {start_date}: {e}")
        finally:
            db.close()

    today = date.today()
    current_week_start = today - timedelta(days=today.weekday())
    last_week_start = current_week_start - timedelta(days=7)
    
    # Aggregate Last Week (Finalize)
    aggregate_week(last_week_start)
    
    # Aggregate Current Week (Live update)
    aggregate_week(current_week_start)
    
    # Cleanup Old Data in Batches
    # Delete DailyActivity older than current week start
    db = SessionLocal()
    try:
        while True:
            # Delete in chunks to avoid locking table for too long
            # SQLite doesn't support 'limit' in delete directly usually unless compiled with it, 
            # but SQLAlchemy generic delete might not use limit.
            # We can select IDs first.
            ids_to_delete = db.query(DailyActivity.id).filter(
                DailyActivity.date < current_week_start
            ).limit(batch_size).all()
            
            if not ids_to_delete:
                break
                
            id_list = [id[0] for id in ids_to_delete]
            db.query(DailyActivity).filter(DailyActivity.id.in_(id_list)).delete(synchronize_session=False)
            db.commit()
            
        logger.info("Weekly activity aggregation and cleanup completed")
    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")
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

    # Weekly Feedback Generation (e.g., Every Saturday at 3 AM)
    feedback_service = FeedbackService()
    
    def run_feedback_generation():
         asyncio.run(feedback_service.generate_weekly_feedback())

    scheduler.add_job(run_feedback_generation, 'cron', day_of_week='sat', hour=3, timezone='Asia/Kolkata')

    scheduler.start()

@app.get("/health")
def health_check():
    return {"status": "ok"}
