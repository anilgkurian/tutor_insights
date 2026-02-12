from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from src.dependencies import validate_token
from src.database import get_db
from src.config import settings
import redis
import logging
from datetime import datetime

router = APIRouter(
    prefix="/activity",
    tags=["activity"]
)

logger = logging.getLogger("tutor_insights")

# Redis Connection
try:
    redis_client = redis.from_url(settings.REDIS_HOST, decode_responses=True)
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None

@router.post("/heartbeat")
async def record_heartbeat(
    student_id: str = Body(..., embed=True),
    subject: str = Body("General", embed=True),
    token_data: dict = Depends(validate_token)
):
    """
    Receives a heartbeat from the frontend indicating active student engagement.
    Increments activity counter in Redis for the current date.
    Each heartbeat represents 30 seconds of activity.
    Subject is optional, defaults to 'General'.
    """
    if not redis_client:
        raise HTTPException(status_code=503, detail="Activity tracking unavailable")

    # Validate that the token belongs to the user or is a parent acting for a student? 
    # For now, we trust the student_id passed, but realistically we should check 
    # if token_data['user_id'] matches student_id or has permission.
    # Assuming token_data['user_id'] is the authenticated user.
    
    # Simple validation: ensure student_id is present
    if not student_id:
        raise HTTPException(status_code=400, detail="Student ID is required")

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    # Key format: activity:student_id:subject:date
    key = f"activity:{student_id}:{subject}:{today_str}"
    
    try:
        # Increment by 30 seconds
        redis_client.incrby(key, 30)
        # Set expiry to 48 hours to ensure data persists until background job runs
        redis_client.expire(key, 172800) 
        return {"status": "ok", "message": "Heartbeat recorded"}
    except Exception as e:
        logger.error(f"Redis error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
