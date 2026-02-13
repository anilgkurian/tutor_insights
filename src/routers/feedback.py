from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Feedback
from typing import Optional
from ..dependencies import validate_token

router = APIRouter(
    prefix="/feedback",
    tags=["feedback"],
    responses={404: {"description": "Not found"}},
)

from ..services.quota_service import quota_service
from ..constants import FEATURE_BASIC_FEEDBACK_REPORT

@router.get("/", response_model=dict)
async def get_feedback(subject: str, session: dict = Depends(validate_token), db: Session = Depends(get_db)):
    """
    Retrieve the latest feedback for a given profile and subject.
    """
    profile_id = session.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="Profile ID not found in context Header")

    has_feature = await quota_service.check_feature(profile_id, FEATURE_BASIC_FEEDBACK_REPORT)
    if not has_feature:
        raise HTTPException(status_code=403, detail="Feedback report is not part of the plan, please upgrade your plan")

    feedback = db.query(Feedback).filter(
        Feedback.profile_id == profile_id,
        Feedback.subject == subject
    ).order_by(Feedback.created_at.desc()).first()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    return {
        "profile_id": feedback.profile_id,
        "subject": feedback.subject,
        "feedback_text": feedback.feedback_text,
        "generated_at": feedback.updated_at
    }
