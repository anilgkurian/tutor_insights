from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import logging
from src.config import settings

logger = logging.getLogger("tutor_insights")

# Session management
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

PUBLIC_KEY = None
if settings.PUBLIC_KEY_BYTES:
    try:
        PUBLIC_KEY = serialization.load_ssh_public_key(
            settings.PUBLIC_KEY_BYTES,
            backend=default_backend()
        )
    except Exception as e:
        logger.warning(f"Failed to load PUBLIC_KEY: {e}")

async def validate_token(token: str = Depends(oauth2_scheme)):
    """
    Dependency to validate the session token.
    For insights, we mainly care that it's a valid admin token.
    """
    if not PUBLIC_KEY:
        logger.error("PUBLIC_KEY not loaded. Cannot validate token.")
        raise HTTPException(status_code=500, detail="Server configuration error")

    try:        
        # Validate JWT
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        return {"user_id": user_id, "token": token}

    except jwt.InvalidTokenError as e:
        logger.error(f"JWT Verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid session token")

async def validate_admin_access(session: dict = Depends(validate_token)):
    user_id = session.get("user_id")
    if user_id != settings.ADMIN_USERNAME:
         logger.warning(f"Access denied for user {user_id}. Admin only.")
         raise HTTPException(status_code=403, detail="Admin access required")
    return session
