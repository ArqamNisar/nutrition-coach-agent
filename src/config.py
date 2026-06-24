import os
from pathlib import Path
from dotenv import load_dotenv

from src.logger import get_logger

logger = get_logger(__name__)

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
USDA_API_KEY = os.getenv("USDA_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///nutrition_coach.db")

logger.info("Configuration loaded successfully.")

# Simple validation
if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY is not set. Please create a .env file based on .env.example and add your Groq API key.")

