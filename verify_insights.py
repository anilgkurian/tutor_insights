import requests
import time
import json
import boto3
import uuid
from datetime import datetime
from src.database import SessionLocal
from src.models import TestPapers, QuestionsAsked, TestPapersMonthly, QuestionsAskedWeekly

# Helper to clear DB
def clear_db():
    db = SessionLocal()
    db.query(TestPapers).delete()
    db.query(QuestionsAsked).delete()
    db.query(TestPapersMonthly).delete()
    db.query(QuestionsAskedWeekly).delete()
    db.commit()
    db.close()
    print("DB Cleared")

# Helper to publish to LocalStack SQS
def publish_sqs(queue_url, message):
    sqs = boto3.client("sqs", region_name="ap-south-1", endpoint_url="http://localhost:4566",
                       aws_access_key_id="test", aws_secret_access_key="test")
    # Retrieve Queue URL if not explicit (but we pass explicit for verification)
    sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
    print(f"Published event: {message.get('event_type')}")
    
def verify_service():
    # 1. Check Health
    try:
        r = requests.get("http://localhost:8000/health")
        if r.status_code != 200:
            print("Service not healthy")
            return
        print("Service Healthy")
    except Exception:
        print("Service not running on port 8000")
        return

    # 2. Publish Events
    exam_queue = "http://localhost:4566/000000000000/tutor_examiner_queue"
    # Needs to ensure queues exist
    sqs = boto3.client("sqs", region_name="ap-south-1", endpoint_url="http://localhost:4566",
                       aws_access_key_id="test", aws_secret_access_key="test")
    
    exam_q_url = sqs.create_queue(QueueName="tutor_examiner_queue")["QueueUrl"]
    tutor_q_url = sqs.create_queue(QueueName="tutor_queue")["QueueUrl"]
    
    print(f"Exam Queue: {exam_q_url}")
    print(f"Tutor Queue: {tutor_q_url}")

    event1 = {
        "event_id": str(uuid.uuid4()),
        "user_id": "u1",
        "profile_id": "p1",
        "class_name": "Class 10",
        "subject": "Math",
        "event_type": "TEST_PAPER_GENERATED",
        "data": {"foo": "bar"},
        "timestamp": datetime.utcnow().isoformat()
    }
    publish_sqs(exam_q_url, event1)
    
    event2 = {
        "event_id": str(uuid.uuid4()),
        "user_id": "u1",
        "profile_id": "p1",
        "class_name": "Class 10",
        "subject": "Science",
        "event_type": "QUESTION_ASKED",
        "data": {"q": "why sky blue"},
        "timestamp": datetime.utcnow().isoformat()
    }
    publish_sqs(tutor_q_url, event2)
    
    # 3. Wait for processing
    print("Waiting for consumers...")
    time.sleep(10)
    
    # 4. Verify DB
    db = SessionLocal()
    tp = db.query(TestPapers).filter_by(event_id=event1["event_id"]).first()
    qa = db.query(QuestionsAsked).filter_by(event_id=event2["event_id"]).first()
    
    if tp:
        print("PASS: Test Paper Event saved")
    else:
        print("FAIL: Test Paper Event NOT saved")
        
    if qa:
        print("PASS: Question Event saved")
    else:
        print("FAIL: Question Event NOT saved")
        
    db.close()

if __name__ == "__main__":
    verify_service()
