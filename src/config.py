from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    INSIGHTS_DB_URL: str = os.getenv("INSIGHTS_DB_URL", "sqlite:///./tutor_insights.db")

    # Auth
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
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
