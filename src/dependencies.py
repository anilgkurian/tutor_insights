from fastapi import HTTPException, Depends, Header
from fastapi.security import OAuth2PasswordBearer
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from src.logger import set_user_id, warning, error
import os
from typing import Optional

from src.config import settings

# Session management
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

PUBLIC_KEY = None
if settings.PUBLIC_KEY:
    try:
        PUBLIC_KEY = serialization.load_ssh_public_key(
            settings.PUBLIC_KEY.replace("\\n", "\n").encode(),
            backend=default_backend()
        )
    except Exception as e:
        warning(f"Failed to load PUBLIC_KEY: {e}")

async def validate_token(
    sessionToken: str = Depends(oauth2_scheme),
    x_student_id: Optional[str] = Header(default=None, alias="X-Student-Id"),
    x_student_name: Optional[str] = Header(default=None, alias="X-Student-Name"),
    x_user_name: Optional[str] = Header(default=None, alias="X-User-Name"),
    x_class: Optional[str] = Header(default=None, alias="X-Class")
):
    """
    Dependency to validate the session token statelessly and set context from headers.
    """
    try:        
        # Validate JWT and get user_id
        # PyJWT decode
        payload = jwt.decode(sessionToken, PUBLIC_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            error(f"Invalid token ERR96")
            raise HTTPException(status_code=401, detail="Invalid token ERR96")
        
        # Validate student matches user if student context is present
        if x_student_id and not x_student_id.startswith(user_id):
            error(f"{x_student_id} Student does not belong to user {user_id} ERR96")
            raise HTTPException(status_code=403, detail="Invalid request ERR96")
        
        # Construct session context (stateless)
        session = {
            "user_id": user_id,
            "profile_id": x_student_id, # Optional, present if student context active
            "student_name": x_student_name, # Optional, present if student context active
            "class": x_class,           # Optional, present if student context active
            "user_name": x_user_name,
            "token": sessionToken
        }
        
        # Set session context for logging
        set_user_id(x_student_id)
            
        return session

    except jwt.InvalidTokenError as e:
        error(f"JWT Verification failed: {e} ERR96")
        raise HTTPException(status_code=401, detail="Invalid session token ERR96")

async def validate_admin_access(session: dict = Depends(validate_token)):
    """
    Dependency to validate admin access.
    Currently just validates token presence via validate_token.
    """
    return session
