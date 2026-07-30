import sys
from pathlib import Path

from loguru import logger


def setup_logging(log_level: str = "INFO", log_file: Path | None = None) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> — <level>{message}</level>",
    )
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(log_file),
            level=log_level,
            rotation="10 MB",
            retention="30 days",
            encoding="utf-8",
        )
