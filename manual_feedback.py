import asyncio
import sys
import os
import warnings
import logging

# Suppress Pydantic V1 compatibility warnings from LangChain on Python 3.14
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")

# Add the current directory to sys.path to ensure 'src' module is found
sys.path.append(os.getcwd())

# Configure logging to see output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from src.services.feedback_service import FeedbackService

async def main():
    service = FeedbackService()
    await service.generate_weekly_feedback()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
