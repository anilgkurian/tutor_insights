from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func
from .database import SessionLocal
from .models import TestPapers, TestPapersMonthly
from .config import settings
import logging
import datetime

logger = logging.getLogger("tutor_insights")

def aggregate_test_papers():
    logger.info("Running Test Papers Aggregation...")
    db = SessionLocal()
    try:
        # Retention Policy: > 30 Days
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=settings.TEST_PAPER_RETENTION_DAYS)
        
        # SQLite compatible date functions
        # month_start: strftime('%Y-%m-01', timestamp)
        
        results = db.query(
            TestPapers.class_name,
            TestPapers.subject,
            func.strftime('%Y-%m-01', TestPapers.timestamp).label('month_start_str'),
            func.count(TestPapers.id).label('count')
        ).filter(
            TestPapers.timestamp < cutoff_date
        ).group_by(
            TestPapers.class_name,
            TestPapers.subject,
            func.strftime('%Y-%m-01', TestPapers.timestamp)
        ).all()
        
        for row in results:
            try:
                # SQLite returns YYYY-MM-01 usually without time if format is just date
                month_start_dt = datetime.datetime.strptime(row.month_start_str, "%Y-%m-%d")
            except:
                # fallback
                month_start_dt = datetime.datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Update or Insert into Monthly table
            # Check existing
            existing = db.query(TestPapersMonthly).filter(
                TestPapersMonthly.class_name == row.class_name,
                TestPapersMonthly.subject == row.subject,
                TestPapersMonthly.month_start == month_start_dt
            ).first()
            
            if existing:
                existing.no_of_tests += row.count
            else:
                new_record = TestPapersMonthly(
                    class_name=row.class_name,
                    subject=row.subject,
                    month_start=month_start_dt,
                    no_of_tests=row.count
                )
                db.add(new_record)
        
        db.commit()
        
        # 2. Delete aggregated data
        deleted = db.query(TestPapers).filter(TestPapers.timestamp < cutoff_date).delete(synchronize_session=False)
        db.commit()
        logger.info(f"Aggregated test papers. Deleted {deleted} old records.")
        
    except Exception as e:
        logger.error(f"Error aggregating test papers: {e}")
        db.rollback()
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Run Test Papers Aggregation: 1st of every month at 3 AM IST (Asia/Kolkata)
    scheduler.add_job(aggregate_test_papers, 'cron', day='1', hour='3', timezone='Asia/Kolkata')
    
    scheduler.start()
    logger.info("Scheduler started.")
