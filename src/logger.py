import logging
import contextvars
from datetime import datetime
from zoneinfo import ZoneInfo
import sys

logger = logging.getLogger('tutor_insights')
session_context = contextvars.ContextVar("session_uuid", default=None)
request_context = contextvars.ContextVar("request_id", default=None)

class ISTFormatter(logging.Formatter):
    """
    Formatter to convert timestamp to IST (Asia/Kolkata).
    """
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=ZoneInfo("UTC"))
        ist_dt = dt.astimezone(ZoneInfo("Asia/Kolkata"))
        if datefmt:
            return ist_dt.strftime(datefmt)
        else:
            return ist_dt.isoformat()

def setup_logging():
    """
    Configure logging to use ISTFormatter for standard output.
    This should be called during application startup.
    """
    # Remove existing handlers to avoid duplicates if re-initialized
    
    handler = logging.StreamHandler(sys.stdout)
    formatter = ISTFormatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S %Z')
    handler.setFormatter(formatter)
    
    # Configure logger
    # uvicorn_logger = logging.getLogger('tutor_insights') # or root
    logger.handlers = [] # clear existing handlers
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    

def set_user_id(user_id: str):
    session_context.set(user_id)

def get_user_id() -> str:
    return session_context.get()

def set_request_id(request_id: str):
    request_context.set(request_id)

def get_request_id() -> str:
    return request_context.get()

def _format_message(message: str) -> str:
    user_id = session_context.get()
    request_id = request_context.get()
    
    prefix = ""
    if request_id:
        prefix += f"[Request: {request_id}] "
    if user_id:
        prefix += f"[User: {user_id}] "
        
    if prefix:
        return f"{prefix.strip()} {message}"
    return message

def log(message: str):
    if not logger.handlers:
        setup_logging()
    logger.info(_format_message(message))

def debug(message: str):
    if not logger.handlers:
        setup_logging()
    logger.debug(_format_message(message))

def warning(message: str):
    if not logger.handlers:
        setup_logging()
    logger.warning(_format_message(message))

def error(message: str):
    if not logger.handlers:
        setup_logging()
    logger.error(_format_message(message))
