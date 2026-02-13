from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, func, UniqueConstraint, Date
from .database import Base
import datetime
import uuid

# Using generic types for compatibility (SQLite/Postgres)
# IDs are stored as Strings (UUID hex)

class TestPapers(Base):
    __tablename__ = "test_papers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, unique=True, index=True)
    user_id = Column(String, index=True)
    profile_id = Column(String, index=True)
    class_name = Column(String, index=True) 
    subject = Column(String, index=True)
    data = Column(JSON)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class TestPapersMonthly(Base):
    __tablename__ = "test_papers_monthly"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    class_name = Column(String, index=True)
    subject = Column(String, index=True)
    no_of_tests = Column(Integer, default=0)
    month_start = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('class_name', 'subject', 'month_start', name='uix_test_monthly'),
    )

class QuestionsAsked(Base):
    __tablename__ = "questions_asked"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, unique=True, index=True)
    user_id = Column(String, index=True)
    profile_id = Column(String, index=True)
    class_name = Column(String, index=True) 
    subject = Column(String, index=True)
    data = Column(JSON)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class QuestionsAskedWeekly(Base):
    __tablename__ = "questions_asked_weekly"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    class_name = Column(String, index=True)
    subject = Column(String, index=True)
    no_of_questions = Column(Integer, default=0)
    # week_start stores the date of the Monday of the week
    week_start = Column(Date)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('class_name', 'subject', 'week_start', name='uix_question_weekly'),
    )

class DailyActivity(Base):
    __tablename__ = "daily_activity"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, index=True, nullable=False)
    date = Column(Date, nullable=False, index=True)
    seconds_active = Column(Integer, default=0)
    subject = Column(String, index=True, nullable=True)

    __table_args__ = (
        UniqueConstraint('student_id', 'subject', 'date', name='uq_daily_activity_student_subject_date'),
    )

class WeeklyActivity(Base):
    __tablename__ = "weekly_activity"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, index=True, nullable=False)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    seconds_active = Column(Integer, default=0)
    subject = Column(String, index=True, nullable=True)

    __table_args__ = (
        UniqueConstraint('student_id', 'subject', 'week_start', name='uq_weekly_activity_student_subject_week'),
    )

class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(String, index=True)
    subject = Column(String, index=True)
    feedback_text = Column(String) # Text
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('profile_id', 'subject', 'created_at', name='uq_feedback_profile_subject_date'), 
        # Actually we might want one per week, but 'created_at' makes it unique per generation. 
        # If we want to overwrite 'current week's' feedback if generated multiple times?
        # The prompt said "store... overwriting previous one". 
        # "store the generated feedback in db per student profile per subject(overwriting previous one)"
        # This implies we only keep THE latest feedback? Or just overwrite if run multiple times same week?
        # "overwriting previous one" usually means a single record per student per subject that gets updated.
        # BUT "trigger a weekly job to generate feedback". History of feedback is valuable.
        # "overwriting previous one" might refer to the "latest" view.
        # Let's assume we keep history but maybe the UI shows the latest.
        # VALIDATION: "overwriting previous one" -> likely means Single Record implementation for now.
    )

