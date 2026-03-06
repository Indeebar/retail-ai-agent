import os
import logging

logger = logging.getLogger(__name__)

REQUIRED_KEYS = [
    "GROQ_API_KEY",
    "QDRANT_URL",
    "QDRANT_API_KEY",
    "UPSTASH_REDIS_REST_URL",
    "UPSTASH_REDIS_REST_TOKEN",
]

def validate_env():
    """
    Run on startup. Crashes loudly with the exact missing key name
    if any required environment variable is not set.
    """
    missing = []
    for key in REQUIRED_KEYS:
        value = os.getenv(key)
        if not value or value.startswith("your_"):
            missing.append(key)
    
    if missing:
        raise RuntimeError(
            f"STARTUP FAILED — Missing required environment variables: {missing}\n"
            f"Check your .env file and make sure all values are filled in."
        )
    
    logger.info("✅ All environment variables validated successfully.")
