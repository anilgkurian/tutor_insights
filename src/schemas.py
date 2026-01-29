from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any

class QuestionAskedOut(BaseModel):
    id: int
    event_id: Optional[str] = None
    user_id: Optional[str] = None
    profile_id: Optional[str] = None
    class_name: Optional[str] = None
    subject: Optional[str] = None
    data: Optional[Any] = None
    timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class QuestionsWeeklyOut(BaseModel):
    id: int
    class_name: Optional[str] = None
    subject: Optional[str] = None
    no_of_questions: int
    week_start: datetime
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TestPaperOut(BaseModel):
    id: int
    event_id: Optional[str] = None
    user_id: Optional[str] = None
    profile_id: Optional[str] = None
    class_name: Optional[str] = None
    subject: Optional[str] = None
    data: Optional[Any] = None
    timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TestPaperMonthlyOut(BaseModel):
    id: int
    class_name: Optional[str] = None
    subject: Optional[str] = None
    no_of_tests: int
    month_start: datetime
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DashboardStatsOut(BaseModel):
    total_questions: int
    questions_yesterday: int
    questions_last_7_days: int
    total_test_papers: int
    test_papers_yesterday: int
    test_papers_last_7_days: int

class ClassSubjectStatsOut(BaseModel):
    class_name: str
    subject: str
    count: int
