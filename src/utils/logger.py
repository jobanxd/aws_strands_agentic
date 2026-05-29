"""
utils/logger.py
───────────────
Single logger used across all agents and tools.
Import this instead of print() or the stdlib logging module.
"""

from loguru import logger
from src.core.settings import settings

logger.remove()
logger.add(
    sink=lambda msg: print(msg, end=""),
    level=settings.LOG_LEVEL,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - {message}",
    colorize=True,
)

__all__ = ["logger"]
