import logging
import json
import redis.asyncio as redis
from sqlalchemy.orm import Session
from datetime import datetime
from ..models import Feedback
from ..config import settings
from ..database import SessionLocal
from src.config import settings

from langchain_openai import ChatOpenAI
import aiohttp

logger = logging.getLogger("tutor_insights")

class FeedbackService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0, # Assuming db 0 is used for chat history as per tutor_service
            decode_responses=True
        )
        self.llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)

    async def get_eligible_profiles(self) -> list[str]:
        """
        Fetches profiles with 'BASIC_FEEDBACK_REPORT' feature enabled from tutor_account.
        """
        url = f"{settings.ACCOUNT_SERVICE_URL}/features/profiles/BASIC_FEEDBACK_REPORT" # TODO: Check port/URL config
    
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to fetch eligible profiles: {response.status}")
                        return []
            except Exception as e:
                logger.error(f"Error connecting to tutor_account: {e}")
                return []

    async def get_chat_history_summary(self, profile_id: str, subject: str):
        """
        Fetches chat history and summary from Redis.
        Keys match tutor_service: 
        summary_key = f"summary:{student_profile_id}:{subject}"
        chat_key = f"chat:{student_profile_id}:{subject}"
        """
        summary_key = f"summary:{profile_id}:{subject}"
        chat_key = f"chat:{profile_id}:{subject}"
        
        summary = await self.redis_client.get(summary_key) or ""
        chat_history_json = await self.redis_client.lrange(chat_key, 0, -1)
        chat_history = [json.loads(msg) for msg in chat_history_json]
        
        # Format for LLM
        formatted_history = "\n".join([f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in chat_history])
        
        return summary, formatted_history

    async def generate_feedback_text(self, profile_id: str, subject: str, summary: str, chat_history: str) -> str:
        if not summary and not chat_history:
            return None

        prompt = f"""
        You are an AI tutor assistant. A parent wants a weekly progress report for their child on subject {subject}.
        Based on the following data, provide a concise summary report.

        Recent Chat History:
        {chat_history[-2000:]} # Limit context if too long
        
        Past Conversation Summaries:
        {summary}
        
        Please include:
        1. Topics Covered
        2. Questions asked: What kind of questions are they asking mostly?
        3. Confusions: What are the main confusions the student has?
        4. Key Strengths & Weaknesses
        5. Engagement Level
        
        Be clear and concise. Do not include technical details about the AI or system.
        Format as Markdown.
        """
        
        try:
            response = await self.llm.ainvoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"Error generating feedback for {profile_id}:{subject}: {e}")
            return None

    async def save_feedback(self, profile_id: str, subject: str, feedback_text: str):
        db = SessionLocal()
        try:
            # Check for existing feedback for this profile/subject to overwrite
            # "overwriting previous one" - implies we keep one record per profile/subject?
            # Or one per week? "trigger a weekly job".
            # If we overwrite, we just update.
            existing = db.query(Feedback).filter(
                Feedback.profile_id == profile_id,
                Feedback.subject == subject
            ).first()
            
            if existing:
                existing.feedback_text = feedback_text
                existing.updated_at = datetime.utcnow()
            else:
                feedback = Feedback(
                    profile_id=profile_id,
                    subject=subject,
                    feedback_text=feedback_text
                )
                db.add(feedback)
            db.commit()
        except Exception as e:
            logger.error(f"Error saving feedback for {profile_id}:{subject}: {e}")
            db.rollback()
        finally:
            db.close()

    async def generate_weekly_feedback(self):
        logger.info("Starting weekly feedback generation...")
        profiles = await self.get_eligible_profiles()
        logger.info(f"Found {len(profiles)} eligible profiles.")
        
        for profile_id in profiles:
            # Scan for subjects this user has chatted in
            # pattern: chat:{profile_id}:*
            # extract subject from key
            cursor = '0'
            user_subjects = set()
            while cursor != 0:
                cursor, keys = await self.redis_client.scan(cursor=cursor, match=f"chat:{profile_id}:*", count=100)
                for key in keys:
                    # key: chat:profile_id:subject
                    parts = key.split(":")
                    if len(parts) >= 3:
                        user_subjects.add(parts[2])
            
            if not user_subjects:
                continue

            for subject in user_subjects:
                try:
                    summary, chat_history = await self.get_chat_history_summary(profile_id, subject)
                    if not summary and not chat_history:
                        continue
                        
                    feedback_text = await self.generate_feedback_text(profile_id, subject, summary, chat_history)
                    if feedback_text:
                        await self.save_feedback(profile_id, subject, feedback_text)
                        logger.info(f"Generated feedback for {profile_id} - {subject}")
                except Exception as e:
                    logger.error(f"Failed to process {profile_id} - {subject}: {e}")
        
        logger.info("Weekly feedback generation completed.")

def main():
    feedback_service = FeedbackService()
    feedback_service.generate_weekly_feedback()