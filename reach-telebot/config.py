# config.py
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FIREBASE_SERVICE_ACCOUNT_KEY_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH")

# Language settings
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
SUPPORTED_LANGUAGES = [lang.strip() for lang in os.getenv("SUPPORTED_LANGUAGES", "en,bn,ta").split(',')]

# Validation
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN environment variable")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY environment variable")
if not FIREBASE_SERVICE_ACCOUNT_KEY_PATH:
    raise ValueError("Missing FIREBASE_SERVICE_ACCOUNT_KEY_PATH environment variable")
if DEFAULT_LANGUAGE not in SUPPORTED_LANGUAGES:
    raise ValueError(f"Default language '{DEFAULT_LANGUAGE}' not in SUPPORTED_LANGUAGES")

logging.info(f"Supported languages: {SUPPORTED_LANGUAGES}")
logging.info(f"Default language: {DEFAULT_LANGUAGE}")