from fastapi import FastAPI
import threading
import logging
from .database import engine, Base
from .consumers import run_consumer, process_examiner_event, process_tutor_event
from .config import settings
from .aggregator import start_scheduler
from .routers import insights
from fastapi.middleware.cors import CORSMiddleware

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tutor_insights")

# Create Tables (for now, in prod use migration)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tutor Insights Service")

# CORS for direct access if needed (proxy is primary)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173", "http://localhost:4501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(insights.router)

@app.on_event("startup")
def startup_event():
    # Start Examiner Consumer
    if settings.EXAMINER_QUEUE_URL:
        t1 = threading.Thread(
            target=run_consumer, 
            args=(settings.EXAMINER_QUEUE_URL, process_examiner_event, "tutor_examiner_queue"),
            daemon=True
        )
        t1.start()

    # Start Tutor Consumer
    if settings.TUTOR_QUEUE_URL:
        t2 = threading.Thread(
            target=run_consumer, 
            args=(settings.TUTOR_QUEUE_URL, process_tutor_event, "tutor_account_queue"),
            daemon=True
        )
        t2.start()

    # Start Aggregator Scheduler
    start_scheduler()

@app.get("/health")
def health_check():
    return {"status": "ok"}
