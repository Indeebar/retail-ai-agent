import logging
import time
from dotenv import load_dotenv
from utils.env_validator import validate_env
from utils.logger import setup_logger
from rag.indexer import run_indexer

load_dotenv()
setup_logger()
logger = logging.getLogger(__name__)

def run_startup():
    """
    Called once when the FastAPI server starts.
    Validates environment, then runs the RAG indexer.
    """
    logger.info("=" * 50)
    logger.info("RETAIL AI AGENT — STARTING UP")
    logger.info("=" * 50)

    # Step 1: Validate all environment variables
    validate_env()

    # Step 2: Run RAG indexer (idempotent — safe to call every startup)
    logger.info("Running RAG indexer...")
    start = time.time()
    run_indexer()
    elapsed = round(time.time() - start, 2)
    logger.info(f"RAG indexer completed in {elapsed}s")

    logger.info("=" * 50)
    logger.info("STARTUP COMPLETE — Server ready")
    logger.info("=" * 50)
