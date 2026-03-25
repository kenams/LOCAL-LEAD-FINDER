"""
Logging configuration
"""
from pathlib import Path
import logging
from app.core.config import settings

def setup_logging(run_log_file: Path | None = None):
    """Setup logging configuration with an optional per-run log file."""
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(str(settings.LOG_FILE), encoding='utf-8'),
    ]
    if run_log_file:
        run_log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(str(run_log_file), encoding='utf-8'))

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True,
    )

    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
