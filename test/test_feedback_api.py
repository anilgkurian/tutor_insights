import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from src.main import app
from src.dependencies import validate_token
from src.database import get_db
from src.models import Feedback
from src.services.quota_service import quota_service
from datetime import datetime

client = TestClient(app)

# Mock DB Session
mock_db = MagicMock()

# Mock Dependency
async def mock_validate_token():
    return {
        "user_id": "user123",
        "profile_id": "student123",
        "token": "valid_token"
    }

def override_get_db():
    try:
        yield mock_db
    finally:
        pass

app.dependency_overrides[validate_token] = mock_validate_token
app.dependency_overrides[get_db] = override_get_db

def test_get_feedback_success():
    # Setup mock return
    mock_feedback = MagicMock()
    mock_feedback.profile_id = "student123"
    mock_feedback.subject = "Math"
    mock_feedback.feedback_text = "Good progress"
    mock_feedback.created_at = datetime.now()
    
    # Mocking the chain: db.query().filter().order_by().first()
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_feedback
    
    # Mock quota_service.check_feature
    app.dependency_overrides[quota_service.check_feature] = AsyncMock(return_value=True)

    with patch("src.routers.feedback.quota_service.check_feature", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        response = client.get("/api/v1/feedback/?subject=Math")
        
    assert response.status_code == 200
    data = response.json()
    assert data["subject"] == "Math"
    assert data["feedback_text"] == "Good progress"
    assert data["profile_id"] == "student123"


def test_get_feedback_not_found():
    # Mock return None
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    
    with patch("src.routers.feedback.quota_service.check_feature", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        response = client.get("/api/v1/feedback/?subject=Science")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Feedback not found"

def test_get_feedback_missing_profile_in_session():
    # Override dependency to simulate missing profile_id
    async def mock_no_profile_token():
        return {
            "user_id": "user123",
            # No profile_id
            "token": "valid_token"
        }
    
    app.dependency_overrides[validate_token] = mock_no_profile_token
    
    response = client.get("/api/v1/feedback/?subject=Math")
    
    assert response.status_code == 400
    assert "Profile ID not found" in response.json()["detail"]
    
    # Reset override
    app.dependency_overrides[validate_token] = mock_validate_token

def test_get_feedback_feature_disabled():
    # Mock return None
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    
    with patch("src.routers.feedback.quota_service.check_feature", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = False
        response = client.get("/api/v1/feedback/?subject=Math")
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Feedback report is not part of the plan, please upgrade your plan"
