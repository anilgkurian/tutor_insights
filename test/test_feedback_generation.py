
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.feedback_service import FeedbackService
from src.models import Feedback
from src.database import SessionLocal
import pytest

# Mock settings
with patch("src.config.settings") as mock_settings:
    mock_settings.REDIS_HOST = "localhost"
    mock_settings.REDIS_PORT = 6379
    mock_settings.OPENAI_API_KEY = "fake-key"

    @pytest.mark.asyncio
    async def test_feedback_generation():
        # Mock dependencies
        mock_redis = MagicMock()
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline
        mock_redis.scan = AsyncMock(side_effect=[
            (10, ["chat:p1:Math", "chat:p1:Science"]), # Non-zero cursor (int)
            (0, []) # End cursor (int)
        ])
        
        # Mock chat history returns
        # get: summary
        # lrange: chat history
        mock_redis.get = AsyncMock(return_value="Student is doing well.")
        mock_redis.lrange = AsyncMock(return_value=[
            '{"role": "user", "content": "What is gravity?"}',
            '{"role": "tutor", "content": "Gravity is..."}'
        ])

        # Mock LLM
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="Generated Feedback: Good progress.")

        # Mock aiohttp
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=["p1"])
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.get.return_value = mock_response
        
        with patch("src.services.feedback_service.redis.Redis", return_value=mock_redis), \
             patch("src.services.feedback_service.ChatOpenAI", return_value=mock_llm), \
             patch("aiohttp.ClientSession", return_value=mock_session), \
             patch("src.services.feedback_service.SessionLocal") as MockSession:

            # Mock DB
            mock_db = MagicMock()
            MockSession.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None # No existing feedback

            service = FeedbackService()
            service.redis_client = mock_redis # Inject mock
            service.llm = mock_llm
            
            await service.generate_weekly_feedback()
            
            # Verification
            # 1. Accounts API called
            mock_session.get.assert_called_with("http://localhost:4501/features/profiles/BASIC_FEEDBACK_REPORT")
            
            # 2. Redis scanned
            assert mock_redis.scan.called
            
            # 3. LLM invoked (Called twice, once for Math, once for Science - roughly, based on side_effect of scan? 
            # Wait, scan raises side_effect returns. 
            # First call returns keys for Math and Science.
            # So loop runs for Math and Science.
            assert mock_llm.ainvoke.call_count >= 1
            
            # 4. DB Add called
            assert mock_db.add.called
            assert mock_db.commit.called
            
            print("Feedback generation test passed!")

if __name__ == "__main__":
    asyncio.run(test_feedback_generation())
