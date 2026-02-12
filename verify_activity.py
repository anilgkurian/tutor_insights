import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from datetime import datetime, date, timedelta
import redis

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.main import app, sync_daily_activity, aggregate_weekly_activity
from src.dependencies import validate_token
from src.config import settings
from src.database import SessionLocal
from src.models import DailyActivity, WeeklyActivity

# Mock Redis
# We can use a real redis if available, or mock it.
# The user env likely has redis running.
# Let's try to use real redis but with a test prefix or just clean up.
try:
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    r.ping()
except:
    print("Redis not available, skipping redis tests")
    sys.exit(0)

client = TestClient(app)

# Override Auth
async def mock_validate_token():
    return {"user_id": "test_student", "token": "mock_token"}

app.dependency_overrides[validate_token] = mock_validate_token

def test_heartbeat_flow():
    student_id = "test_student_subject"
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    today_date = datetime.utcnow().date()
    
    # Keys
    key_math = f"activity:{student_id}:Math:{today_str}"
    key_science = f"activity:{student_id}:Science:{today_str}"
    key_general = f"activity:{student_id}:General:{today_str}" # Default
    
    # 1. Clear existing redis keys
    try:
        r.delete(key_math)
        r.delete(key_science)
        r.delete(key_general)
    except:
        pass
    
    # 2. Send Heartbeats
    # Math
    print(f"Sending heartbeat for Math")
    response = client.post("/api/v1/activity/heartbeat", json={"student_id": student_id, "subject": "Math"})
    assert response.status_code == 200
    val_math = r.get(key_math)
    assert val_math == "30"
    
    # Science
    print(f"Sending heartbeat for Science")
    client.post("/api/v1/activity/heartbeat", json={"student_id": student_id, "subject": "Science"})
    val_science = r.get(key_science)
    assert val_science == "30"
    
    # General (no subject)
    print(f"Sending heartbeat for General (no subject)")
    client.post("/api/v1/activity/heartbeat", json={"student_id": student_id})
    val_general = r.get(key_general)
    assert val_general == "30"
    
    print("✅ Heartbeat API and Redis update verified")
    
    # 3. Verify Sync Daily Activity (Redis -> DB)
    db = SessionLocal()
    # Clear DB for this student
    db.query(DailyActivity).filter_by(student_id=student_id).delete()
    db.commit()
    
    print("Running sync_daily_activity...")
    sync_daily_activity()
    
    # Check Math
    record_math = db.query(DailyActivity).filter_by(student_id=student_id, subject="Math", date=today_date).first()
    assert record_math is not None, "Math record not found"
    assert record_math.seconds_active == 30
    
    # Check Science
    record_science = db.query(DailyActivity).filter_by(student_id=student_id, subject="Science", date=today_date).first()
    assert record_science is not None, "Science record not found"
    assert record_science.seconds_active == 30
    
    # Check General
    record_general = db.query(DailyActivity).filter_by(student_id=student_id, subject="General", date=today_date).first()
    assert record_general is not None, "General record not found"
    assert record_general.seconds_active == 30
    
    print("✅ Daily Activity Sync verified")
    
    # 4. Verify Aggregate Weekly Activity
    db.query(WeeklyActivity).filter_by(student_id=student_id).delete()
    db.commit()
    
    print("Running aggregate_weekly_activity...")
    aggregate_weekly_activity()
    
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    
    weekly_math = db.query(WeeklyActivity).filter_by(student_id=student_id, subject="Math", week_start=start_of_week).first()
    assert weekly_math is not None, "Weekly Math record not found"
    assert weekly_math.seconds_active >= 30
    
    weekly_science = db.query(WeeklyActivity).filter_by(student_id=student_id, subject="Science", week_start=start_of_week).first()
    assert weekly_science is not None, "Weekly Science record not found"
    assert weekly_science.seconds_active >= 30

    weekly_general = db.query(WeeklyActivity).filter_by(student_id=student_id, subject="General", week_start=start_of_week).first()
    assert weekly_general is not None, "Weekly General record not found"
    assert weekly_general.seconds_active >= 30
    
    print(f"✅ Weekly Activity Aggregation verified.")
    
    # 5. Verify Cleanup Logic
    # Insert old data (2 weeks ago)
    two_weeks_ago = today - timedelta(days=14)
    old_record = DailyActivity(
        student_id=student_id,
        subject="History",
        date=two_weeks_ago,
        seconds_active=100
    )
    db.add(old_record)
    
    # Insert last week data (should be aggregated then deleted)
    last_week_date = today - timedelta(days=7)
    last_week_record = DailyActivity(
        student_id=student_id,
        subject="History",
        date=last_week_date,
        seconds_active=200
    )
    db.add(last_week_record)
    db.commit()
    
    print("Running aggregate_weekly_activity again for cleanup check...")
    aggregate_weekly_activity()
    
    # Check if old data is gone
    old_exists = db.query(DailyActivity).filter_by(date=two_weeks_ago).first()
    assert old_exists is None, "Old daily data (2 weeks ago) was not cleaned up"
    
    # Check if last week data is gone
    last_week_exists = db.query(DailyActivity).filter_by(date=last_week_date).first()
    assert last_week_exists is None, "Last week daily data was not cleaned up"
    
    # Check if current daily data still exists
    current_exists = db.query(DailyActivity).filter_by(student_id=student_id, date=today_date).first()
    assert current_exists is not None, "Current daily data was incorrectly deleted"
    
    # Check if History was aggregated for last week
    last_week_start = start_of_week - timedelta(days=7)
    history_weekly = db.query(WeeklyActivity).filter_by(
        student_id=student_id, 
        subject="History", 
        week_start=last_week_start
    ).first()
    assert history_weekly is not None, "Last week history was not aggregated"
    assert history_weekly.seconds_active == 200, "Last week history aggregation value mismatch"
    
    print("✅ Cleanup and Backfill Verification Passed")
    
    # Cleanup
    r.delete(key_math)
    r.delete(key_science)
    r.delete(key_general)
    db.query(DailyActivity).filter_by(student_id=student_id).delete()
    db.query(WeeklyActivity).filter_by(student_id=student_id).delete()
    db.commit()
    db.close()

if __name__ == "__main__":
    try:
        test_heartbeat_flow()
        print("\n🎉 All verifications passed!")
    except AssertionError as e:
        print(f"\n❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
