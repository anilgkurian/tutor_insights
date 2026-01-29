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
