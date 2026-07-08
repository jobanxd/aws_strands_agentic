"""
PostgreSQL database manager for ODD/KYC agents.

This module provides asynchronous database utilities for interacting with
AWS RDS PostgreSQL, including connection pooling, query execution, and
repository-style methods used by agent workflows (agent outputs, final
reports, feedback records, and message logging).
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, NamedTuple
import asyncpg
from dotenv import load_dotenv

from src.core.aws_secret import get_rds_secret
from src.database_rds.repositories.agent_repository import AgentRepository
from src.database_rds.repositories.country_risk_repository import CountryRiskRepository
from src.database_rds.repositories.feedback_repository import FeedbackRepository
from src.database_rds.repositories.final_report_repository import FinalReportRepository
from src.database_rds.repositories.kyc_repository import KYCRepository
from src.database_rds.repositories.servicelink_repository import ServiceLinkRepository
from src.database_rds.repositories.sharepoint_repository import SharePointRepository
from src.database_rds.repositories.tracking_repository import TrackingRepository
from src.database_rds.repositories.textract_repository import TextractRepository

load_dotenv()
logger = logging.getLogger(__name__)
IS_SECRET_MANAGER = str(os.getenv("IS_SECRET_MANAGER")).lower()
DB_SCHEMA = os.getenv("DB_SCHEMA")

# Event loop-specific database manager instances
_db_handlers: Dict[int, "ODDDatabaseManagerPostgreSQL"] = {}


def get_pg_manager():
    """
    Get PostgreSQL manager instance for the current event loop.
    This is an alias for get_db_handler() for backward compatibility.
    """
    return get_db_handler()


class DatabaseConfig(NamedTuple):
    """PostgreSQL connection and pool settings loaded from environment variables."""

    host: str
    database: str
    user: str
    password: str
    port: int = 5432
    db_schema: str = DB_SCHEMA
    min_pool_size: int = 2
    max_pool_size: int = 10
    ssl: str = "require"

    def dsn(self) -> str:
        """Return a PostgreSQL DSN string (without password)."""
        return f"postgresql://{self.user}@{self.host}:{self.port}/{self.database}"

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Construct config from environment variables."""

        if IS_SECRET_MANAGER == "true":
            secret = get_rds_secret()

            return cls(
                host=secret["host"],
                port=secret["port"],
                database=secret["dbname"],
                user=secret["username"],
                password=secret["password"],
            )

        return cls(
            host=os.environ["AWS_RDS_ENDPOINT"],
            database=os.environ["AWS_RDS_DB_NAME"],
            user=os.environ["AWS_RDS_USERNAME"],
            password=os.environ["AWS_RDS_PASSWORD"],
        )


class ODDDatabaseManagerPostgreSQL:
    """
    PostgreSQL database handler for KYC/ODD operations.
    Designed for production use with AWS RDS.
    """

    def __init__(self):
        self.config = DatabaseConfig.from_env()
        self._pool: Optional[asyncpg.Pool] = None
        self._pool_lock = asyncio.Lock()

    @property
    def agent(self) -> AgentRepository:
        """Return the agent repository."""
        return AgentRepository(self)

    @property
    def final_report(self) -> FinalReportRepository:
        """Return the final report repository."""
        return FinalReportRepository(self)

    @property
    def feedback(self) -> FeedbackRepository:
        """Return the feedback repository."""
        return FeedbackRepository(self)

    @property
    def sharepoint(self) -> SharePointRepository:
        """Return the SharePoint repository."""
        return SharePointRepository(self)

    @property
    def kyc(self) -> KYCRepository:
        """Return the KYC repository."""
        return KYCRepository(self)

    @property
    def servicelink(self) -> ServiceLinkRepository:
        """Return the ServiceLink repository."""
        return ServiceLinkRepository(self)

    @property
    def tracking(self) -> TrackingRepository:
        """Return the tracking repository."""
        return TrackingRepository(self)

    @property
    def country_risk(self) -> CountryRiskRepository:
        """Return the country risk repository."""
        return CountryRiskRepository(self)
    
    @property
    def textract(self) -> TextractRepository:
        """Return the textract repository (reads the pre-processing cache table)."""
        return TextractRepository(self)

    async def create_pool(self):
        """Create connection pool with SSL support for AWS RDS"""
        if self._pool is not None:
            return

        async with self._pool_lock:
            if self._pool is not None:
                return

            self._pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                min_size=self.config.min_pool_size,
                max_size=self.config.max_pool_size,
                ssl=self.config.ssl,  # AWS RDS requires SSL
                command_timeout=60,
            )
            logger.info(
                "PostgreSQL connection pool created for %s:%s/%s",
                self.config.host,
                self.config.port,
                self.config.database,
            )

    def get_pool_size(self) -> int:
        """Return current size of connection pool if available"""
        if self._pool is None:
            return 0
        return self._pool.get_size()

    async def close_pool(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")

    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool"""
        if self._pool is None:
            await self.create_pool()

        pool = self._pool
        if pool is None:
            raise RuntimeError("PostgreSQL connection pool is not initialized")

        conn = await pool.acquire()
        try:
            yield conn
        finally:
            await pool.release(conn)

    async def initialize_database(self, session_id: str) -> bool:
        """Test database connectivity."""
        try:
            async with self.get_connection() as conn:
                await conn.fetchval("SELECT 1")

            logger.info("Database initialized for session: %s", session_id)
            return True

        except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError) as e:
            logger.error(
                "Error initializing database for session %s: %s",
                session_id,
                e,
                exc_info=True,
            )
            return False


def get_db_handler() -> "ODDDatabaseManagerPostgreSQL":
    """
    Return a PostgreSQL database handler instance scoped to the current event loop.

    Ensures a single handler per asyncio event loop to avoid cross-loop
    connection pool issues.
    """

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop_id = id(loop)

    if loop_id not in _db_handlers:
        logger.info("Creating database handler for event loop %s", loop_id)
        _db_handlers[loop_id] = ODDDatabaseManagerPostgreSQL()

    return _db_handlers[loop_id]


async def initialize_database(session_id: str) -> bool:
    """
    Initialize PostgreSQL database (connectivity check).

    Uses environment variables if parameters are not provided.
    Kept for backward compatibility with existing imports.
    """
    handler = get_db_handler()
    return await handler.initialize_database(session_id)
