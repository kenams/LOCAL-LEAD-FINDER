"""
Logging configuration
"""
import logging
from app.core.config import settings

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(str(settings.LOG_FILE), encoding='utf-8')
        ]
    )

    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)