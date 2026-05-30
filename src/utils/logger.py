"""
utils/logger.py
───────────────
Standard Python logging with colors for production use with FastAPI/uvicorn.
Fixes inconsistent line positioning caused by Strands printing directly to stdout.
"""

import logging
import sys
from src.core.settings import settings


# ── ANSI color codes ──────────────────────────────────────────────────────────
RESET    = "\033[0m"
GREY     = "\033[38;5;240m"
CYAN     = "\033[36m"
GREEN    = "\033[32m"
YELLOW   = "\033[33m"
RED      = "\033[31m"
BOLD_RED = "\033[1;31m"

LEVEL_COLORS = {
    "DEBUG"   : GREY,
    "INFO"    : GREEN,
    "WARNING" : YELLOW,
    "ERROR"   : RED,
    "CRITICAL": BOLD_RED,
}


# ── Stdout tracker ────────────────────────────────────────────────────────────

class _TrackedStdout:
    """
    Wraps the real stdout so we can detect whether Strands (or anything else)
    left the cursor mid-line before our logger tries to write.
    """

    def __init__(self, original):
        self._original = original
        self.needs_newline = False

    def write(self, msg: str):
        if msg:
            self.needs_newline = not msg.endswith("\n")
        self._original.write(msg)

    def flush(self):
        self._original.flush()

    def fileno(self):
        return self._original.fileno()

    def isatty(self):
        return self._original.isatty()

    # Forward anything else to the original stdout
    def __getattr__(self, name):
        return getattr(self._original, name)


# ── Formatter ─────────────────────────────────────────────────────────────────

class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        level_color = LEVEL_COLORS.get(record.levelname, RESET)
        record.asctime = self.formatTime(record, self.datefmt)
        return (
            f"{GREY}{record.asctime}{RESET} | "
            f"{level_color}{record.levelname:<8}{RESET} | "
            f"{CYAN}{record.name}{RESET} - "
            f"{record.getMessage()}"
        )


# ── Handler ───────────────────────────────────────────────────────────────────

class NewlineHandler(logging.StreamHandler):
    """
    Only prepends a newline when stdout was left mid-line by Strands.
    Keeps log output tight and consistent without extra blank lines.
    """

    def __init__(self, tracked: _TrackedStdout):
        super().__init__(tracked._original)
        self._tracked = tracked

    def emit(self, record: logging.LogRecord):
        try:
            if self._tracked.needs_newline:
                self.stream.write("\n")
                self._tracked.needs_newline = False
            self.stream.write(self.format(record))
            self.stream.write("\n")
            self.flush()
        except Exception:
            self.handleError(record)


# ── Setup ─────────────────────────────────────────────────────────────────────

def setup_logging():
    """
    Configure root logger. Call once at app startup in main.py before
    anything else imports or uses logging.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Wrap stdout so we can track mid-line state
    tracked = _TrackedStdout(sys.stdout)
    sys.stdout = tracked

    handler = NewlineHandler(tracked)
    handler.setFormatter(ColorFormatter(datefmt="%H:%M:%S"))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("strands").setLevel(logging.WARNING)


# ── Public API ────────────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger. Use this in every module.

    Usage:
        from src.utils.logger import get_logger
        logger = get_logger(__name__)
    """
    return logging.getLogger(name)