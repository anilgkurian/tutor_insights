from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, text, func, cast, String
from src.database import get_db
from fastapi import Depends
from src.models import QuestionsAsked, TestPapers, TestPapersMonthly
from src.schemas import QuestionAskedOut, QuestionsWeeklyOut, TestPaperOut, TestPaperMonthlyOut, DashboardStatsOut, ClassSubjectStatsOut
from datetime import datetime, timedelta

from src.dependencies import validate_admin_access

router = APIRouter(
    prefix="/api/insights",
    tags=["insights"],
    dependencies=[Depends(validate_admin_access)]
)

@router.get("/stats/dashboard", response_model=DashboardStatsOut)
def get_dashboard_stats(db: Session = Depends(get_db)):
    return None

@router.get("/stats/questions-by-subject", response_model=List[ClassSubjectStatsOut])
def get_questions_by_subject_stats(db: Session = Depends(get_db)):
    return None

@router.get("/stats/test-papers-by-subject", response_model=List[ClassSubjectStatsOut])
def get_test_papers_by_subject_stats(db: Session = Depends(get_db)):
    # 1. Historical Data (from TestPapersMonthly)
    hist_results = db.query(
        TestPapersMonthly.class_name,
        TestPapersMonthly.subject,
        func.sum(TestPapersMonthly.no_of_tests).label('count')
    ).group_by(
        TestPapersMonthly.class_name,
        TestPapersMonthly.subject
    ).all()

    # 2. Recent Data (from TestPapers)
    recent_results = db.query(
        TestPapers.class_name,
        TestPapers.subject,
        func.count(TestPapers.id).label('count')
    ).group_by(
        TestPapers.class_name,
        TestPapers.subject
    ).all()

    stats_map = {}

    # Initial population from historical
    for row in hist_results:
        key = (row.class_name, row.subject)
        stats_map[key] = stats_map.get(key, 0) + (row.count or 0)

    # Add recent data
    for row in recent_results:
        key = (row.class_name, row.subject)
        stats_map[key] = stats_map.get(key, 0) + (row.count or 0)

    # Convert to list
    final_stats = []
    for (class_name, subject), count in stats_map.items():
        if class_name and subject: # filter out None if any
            final_stats.append(ClassSubjectStatsOut(
                class_name=class_name,
                subject=subject,
                count=count
            ))
    
    # Sort for consistent display (Class then Subject)
    final_stats.sort(key=lambda x: (x.class_name, x.subject))
    
    return final_stats

# --- Questions ---

@router.get("/questions", response_model=List[QuestionAskedOut])
def get_questions(
    page: int = 1,
    limit: int = 50,
    search: str = "",
    sort_by: str = "timestamp",
    sort_order: str = "desc",
    db: Session = Depends(get_db)
):
    query = db.query(QuestionsAsked)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (QuestionsAsked.subject.ilike(search_filter)) |
            (QuestionsAsked.class_name.ilike(search_filter)) |
            (QuestionsAsked.user_id.ilike(search_filter)) |
            (cast(QuestionsAsked.data, String).ilike(search_filter))
        )

    if sort_by:
        field = getattr(QuestionsAsked, sort_by, None)
        if field:
            if sort_order == "desc":
                query = query.order_by(desc(field))
            else:
                query = query.order_by(field)
        else:
            # Default sort
            query = query.order_by(desc(QuestionsAsked.timestamp))
    else:
        query = query.order_by(desc(QuestionsAsked.timestamp))

    offset = (page - 1) * limit
    return query.offset(offset).limit(limit).all()

@router.get("/questions/weekly", response_model=List[QuestionsWeeklyOut])
def get_questions_weekly(
    page: int = 1,
    limit: int = 50,
    search: str = "",
    sort_by: str = "week_start",
    sort_order: str = "desc",
    db: Session = Depends(get_db)
):
    return None

# --- Test Papers ---

@router.get("/test-papers", response_model=List[TestPaperOut])
def get_test_papers(
    page: int = 1,
    limit: int = 50,
    search: str = "",
    sort_by: str = "timestamp",
    sort_order: str = "desc",
    db: Session = Depends(get_db)
):
    query = db.query(TestPapers)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (TestPapers.subject.ilike(search_filter)) |
            (TestPapers.class_name.ilike(search_filter)) |
            (TestPapers.user_id.ilike(search_filter)) |
            (cast(TestPapers.data, String).ilike(search_filter))
        )

    if sort_by:
        field = getattr(TestPapers, sort_by, None)
        if field:
            if sort_order == "desc":
                query = query.order_by(desc(field))
            else:
                query = query.order_by(field)
        else:
            query = query.order_by(desc(TestPapers.timestamp))
    else:
        query = query.order_by(desc(TestPapers.timestamp))

    offset = (page - 1) * limit
    return query.offset(offset).limit(limit).all()

@router.get("/test-papers/monthly", response_model=List[TestPaperMonthlyOut])
def get_test_papers_monthly(
    page: int = 1,
    limit: int = 50,
    search: str = "",
    sort_by: str = "month_start",
    sort_order: str = "desc",
    db: Session = Depends(get_db)
):
    query = db.query(TestPapersMonthly)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (TestPapersMonthly.subject.ilike(search_filter)) |
            (TestPapersMonthly.class_name.ilike(search_filter))
        )

    if sort_by:
        field = getattr(TestPapersMonthly, sort_by, None)
        if field:
            if sort_order == "desc":
                query = query.order_by(desc(field))
            else:
                query = query.order_by(field)
        else:
            query = query.order_by(desc(TestPapersMonthly.month_start))
    else:
        query = query.order_by(desc(TestPapersMonthly.month_start))

    offset = (page - 1) * limit
    return query.offset(offset).limit(limit).all()
