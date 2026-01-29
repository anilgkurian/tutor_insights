import boto3
import json
import time
from sqlalchemy.orm import Session
from .database import SessionLocal
from .config import settings
from .models import TestPapers, QuestionsAsked
import logging
import datetime

logger = logging.getLogger("tutor_insights")

def get_sqs_client():
    return boto3.client(
        "sqs",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_Q_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_Q_SECRET_ACCESS_KEY,
        endpoint_url=settings.AWS_ENDPOINT_URL
    )

def parse_timestamp(ts_str):
    try:
        return datetime.datetime.fromisoformat(ts_str)
    except:
        return datetime.datetime.utcnow()

def process_examiner_event(message_body: str, db: Session):
    try:
        event = json.loads(message_body)
        if event.get("event_type") == "TEST_PAPER_GENERATED":
            logger.info(f"Processing TEST_PAPER_GENERATED: {event.get('event_id')}")
            record = TestPapers(
                event_id=event.get("event_id"),
                user_id=event.get("user_id"),
                profile_id=event.get("profile_id"),
                class_name=event.get("class_name"),
                subject=event.get("subject"),
                data=event.get("data"),
                timestamp=parse_timestamp(event.get("timestamp"))
            )
            db.add(record)
            db.commit()
    except Exception as e:
        logger.error(f"Error processing examiner event: {e}")
        db.rollback()

def process_tutor_event(message_body: str, db: Session):
    try:
        event = json.loads(message_body)
        if event.get("event_type") == "QUESTION_ASKED":
            logger.info(f"Processing QUESTION_ASKED: {event.get('event_id')}")
            record = QuestionsAsked(
                event_id=event.get("event_id"),
                user_id=event.get("user_id"),
                profile_id=event.get("profile_id"),
                class_name=event.get("class_name"),
                subject=event.get("subject"),
                data=event.get("data"),
                timestamp=parse_timestamp(event.get("timestamp"))
            )
            db.add(record)
            db.commit()
    except Exception as e:
        logger.error(f"Error processing tutor event: {e}")
        db.rollback()

def run_consumer(queue_url: str, processor_func, queue_name: str):
    logger.info(f"Starting consumer for {queue_name} at {queue_url}")
    sqs = get_sqs_client()
    
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20
            )
            
            messages = response.get("Messages", [])
            for msg in messages:
                with SessionLocal() as db:
                    processor_func(msg["Body"], db)
                
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=msg["ReceiptHandle"]
                )
                
        except Exception as e:
            logger.error(f"Error in {queue_name} consumer: {e}")
            time.sleep(5)
