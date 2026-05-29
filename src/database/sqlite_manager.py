"""
SQLite database manager for ODD/KYC agents.

Simplified async database layer replacing PostgreSQL asyncpg manager.
Uses aiosqlite for file-based local database access.

This is designed for:
- Local development
- Lightweight runtime
- Simple async repository pattern compatibility
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, NamedTuple

import aiosqlite
from dotenv import load_dotenv

from src.database.repositories.agent_repository import AgentRepository
from src.database.repositories.country_risk_repository import CountryRiskRepository
from src.database.repositories.feedback_repository import FeedbackRepository
from src.database.repositories.final_report_repository import FinalReportRepository
from src.database.repositories.kyc_repository import KYCRepository
from src.database.repositories.servicelink_repository import ServiceLinkRepository
from src.database.repositories.sharepoint_repository import SharePointRepository
from src.database.repositories.tracking_repository import TrackingRepository

load_dotenv()
logger = logging.getLogger(__name__)

# One manager per event loop (kept for compatibility)
_db_handlers: Dict[int, "SQLiteDatabaseManager"] = {}


class DatabaseConfig(NamedTuple):
    """
    SQLite configuration (file-based database).
    """

    db_path: str
    db_schema: str = ""  # kept only for compatibility (not used in SQLite)

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        return cls(
            db_path=os.environ.get("SQLITE_DB_PATH", "src/database/data/kyc_database.db")
        )


class SQLiteDatabaseManager:
    """
    Lightweight SQLite async database manager.
    Replaces PostgreSQL asyncpg + pooling with a simple file DB.
    """

    def __init__(self):
        self.config = DatabaseConfig.from_env()

    # =========================
    # Repository accessors
    # =========================

    @property
    def agent(self) -> AgentRepository:
        return AgentRepository(self)

    @property
    def final_report(self) -> FinalReportRepository:
        return FinalReportRepository(self)

    @property
    def feedback(self) -> FeedbackRepository:
        return FeedbackRepository(self)

    @property
    def sharepoint(self) -> SharePointRepository:
        return SharePointRepository(self)

    @property
    def kyc(self) -> KYCRepository:
        return KYCRepository(self)

    @property
    def servicelink(self) -> ServiceLinkRepository:
        return ServiceLinkRepository(self)

    @property
    def tracking(self) -> TrackingRepository:
        return TrackingRepository(self)

    @property
    def country_risk(self) -> CountryRiskRepository:
        return CountryRiskRepository(self)

    # =========================
    # Connection handling
    # =========================

    @asynccontextmanager
    async def get_connection(self):
        """
        Get SQLite connection (no pooling needed).
        """
        conn = await aiosqlite.connect(self.config.db_path)
        conn.row_factory = aiosqlite.Row

        try:
            yield conn
        finally:
            await conn.close()

    # =========================
    # DB health check
    # =========================

    async def initialize_database(self, session_id: str) -> bool:
        """
        Simple connectivity test for SQLite DB.
        Also ensures DB file is accessible.
        """
        try:
            async with self.get_connection() as conn:
                await conn.execute("SELECT 1")
                await conn.commit()

            logger.info("SQLite database initialized for session: %s", session_id)
            return True

        except Exception as e:
            logger.error(
                "Error initializing SQLite database for session %s: %s",
                session_id,
                e,
                exc_info=True,
            )
            return False


# =========================
# Event loop scoped handler
# =========================

def get_db_handler() -> SQLiteDatabaseManager:
    """
    Return a SQLite database handler instance scoped to current event loop.
    (Kept for compatibility with existing architecture)
    """

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop_id = id(loop)

    if loop_id not in _db_handlers:
        logger.info("Creating SQLite handler for event loop %s", loop_id)
        _db_handlers[loop_id] = SQLiteDatabaseManager()

    return _db_handlers[loop_id]


def get_sqlite_manager() -> SQLiteDatabaseManager:
    """
    Alias for clarity (recommended new usage).
    """
    return get_db_handler()


# =========================
# Backward-compatible helper
# =========================

async def initialize_database(session_id: str) -> bool:
    """
    Backward-compatible initialization function.
    """
    handler = get_db_handler()
    return await handler.initialize_database(session_id)