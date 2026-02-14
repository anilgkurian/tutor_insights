
import asyncio
import sys
import os
import warnings
import logging

# Suppress Pydantic V1 compatibility warnings from LangChain on Python 3.14
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")

# Add the current directory to sys.path to ensure 'src' module is found
# Also change CWD to script directory so relative paths (like DB) work correctly
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.append(script_dir)

# Configure logging to see output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from src.services.question_aggregation_service import QuestionAggregationService

async def main():
    service = QuestionAggregationService()
    await service.aggregate_weekly_questions()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
