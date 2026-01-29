from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    INSIGHTS_DB_URL: str = os.getenv("INSIGHTS_DB_URL", "sqlite:///./tutor_insights.db")
    
    # AWS / SQS
    AWS_REGION: str = "ap-south-1"
    AWS_Q_ACCESS_KEY_ID: str | None = None
    AWS_Q_SECRET_ACCESS_KEY: str | None = None
    AWS_ENDPOINT_URL: str | None = os.getenv("AWS_ENDPOINT_URL")
    
    # Consumer Queues
    EXAMINER_QUEUE_URL: str | None = os.getenv("EXAMINER_QUEUE_URL")
    TUTOR_QUEUE_URL: str | None = os.getenv("TUTOR_QUEUE_URL")

    # Retention config
    TEST_PAPER_RETENTION_DAYS: int = 30
    QUESTION_RETENTION_DAYS: int = 7

    # Auth
    ADMIN_USERNAME: str = "admin"
    ALGORITHM: str = "EdDSA"
    PUBLIC_KEY: str = ""
    PUBLIC_KEY_BYTES: bytes = b""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Process keys
try:
    if settings.PUBLIC_KEY:
        settings.PUBLIC_KEY_BYTES = settings.PUBLIC_KEY.replace("\\n", "\n").encode()
except Exception as e:
    print(f"WARNING: Could not process keys from environment: {e}")
