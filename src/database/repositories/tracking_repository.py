"""
Tracking repository for ODD workflow status.

This module manages database operations related to tracking the
status of ODD investigations for specific sessions and parties.
It supports retrieving the current workflow status and updating
status information as the investigation progresses.

These methods are intended to be used through the
ODDDatabaseManagerPostgreSQL database manager.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TrackingRepository:
    """Repository methods for ODD tracking status."""

    def __init__(self, ctx):
        """Initialize the repository with the database manager context."""
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    async def get_odd_status(
        self, session_id: str, party_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the current ODD status for a given session and party
        """

        query = """
        SELECT session_id,
               party_id,
               status,
               last_updated
        FROM odd_status
        WHERE session_id = ?
          AND party_id = ?
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, session_id, party_id)
            return dict(row) if row else None

    async def update_odd_status(
        self,
        session_id: str,
        party_id: str,
        status_data: Dict[str, Any],
    ) -> bool:
        """
        Insert or update ODD status for a given session and party.
        """

        query = """
        INSERT INTO odd_status (
            session_id,
            party_id,
            status,
            last_updated
        )
        VALUES (
            ?,
            ?,
            ?,
            ?
        )
        ON CONFLICT (session_id, party_id)
        DO UPDATE SET
            status = EXCLUDED.status,
            last_updated = EXCLUDED.last_updated
        """

        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    query,
                    session_id,
                    party_id,
                    status_data.get("status"),
                    None,  # will be set below if needed
                )

            logger.info(
                "Updated ODD status for session %s, party %s",
                session_id,
                party_id,
            )
            return True

        except Exception as e:
            logger.error(
                "Error updating ODD status for session %s, party %s: %s",
                session_id,
                party_id,
                e,
                exc_info=True,
            )
            return False
