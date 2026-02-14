from datetime import datetime, timedelta, date
from sqlalchemy import func
from src.database import SessionLocal
from src.models import QuestionsAsked, QuestionsWeeklyAggr
import logging

logger = logging.getLogger("tutor_insights")

class QuestionAggregationService:
    def __init__(self):
        pass

    async def aggregate_weekly_questions(self):
        """
        Aggregates all questions from QuestionsAsked, stores them in QuestionsWeeklyAggr,
        and deletes the processed records from QuestionsAsked.
        
        Optimized for 500k -> 5k entries.
        """
        logger.info("Starting weekly questions aggregation (Optimized)...")
        db = SessionLocal()
        try:
            today = date.today()
            
            # 1. Aggregate in Database (SQL GROUP BY)
            # This is much faster than fetching 500k rows into Python
            aggregated_results = db.query(
                QuestionsAsked.user_id,
                QuestionsAsked.profile_id,
                QuestionsAsked.class_name,
                QuestionsAsked.subject,
                func.count(QuestionsAsked.id).label('count')
            ).group_by(
                QuestionsAsked.user_id,
                QuestionsAsked.profile_id,
                QuestionsAsked.class_name,
                QuestionsAsked.subject
            ).all()

            if not aggregated_results:
                logger.info("No questions to aggregate.")
                return 

            logger.info(f"Aggregated down to {len(aggregated_results)} groups.")

            # 2. Bulk/Batch Upsert
            # Fetch all existing records for TODAY to avoid N+1 queries during upsert
            existing_records = db.query(QuestionsWeeklyAggr).filter(
                QuestionsWeeklyAggr.date == today
            ).all()
            
            # Create lookup map: (user_id, profile_id, class_name, subject) -> record object
            existing_map = {
                (r.user_id, r.profile_id, r.class_name, r.subject): r 
                for r in existing_records
            }
            
            new_records = []
            
            for row in aggregated_results:
                key = (row.user_id, row.profile_id or "", row.class_name or "", row.subject or "")
                
                if key in existing_map:
                    # Update existing logic
                    existing_record = existing_map[key]
                    existing_record.count += row.count
                else:
                    # Create new
                    new_rec = QuestionsWeeklyAggr(
                        user_id=row.user_id,
                        profile_id=row.profile_id,
                        class_name=row.class_name,
                        subject=row.subject,
                        count=row.count,
                        date=today
                    )
                    new_records.append(new_rec)
            
            if new_records:
                db.bulk_save_objects(new_records)

            # 3. Delete all from QuestionsAsked
            # Efficiently clear the table
            db.query(QuestionsAsked).delete(synchronize_session=False)
            
            db.commit()
            logger.info(f"Weekly questions aggregation completed. Processed {len(aggregated_results)} unique groups.")

        except Exception as e:
            logger.error(f"Error aggregating questions: {e}")
            db.rollback()
        finally:
            db.close()
