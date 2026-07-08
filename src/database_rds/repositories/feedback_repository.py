"""
Feedback repository for final report corrections.

This module provides database operations for storing and retrieving
feedback records related to KYC final reports. Feedback entries track
changes made to report fields, including original values, updated
values, and modification metadata.

The methods defined here are intended to be used through the
ODDDatabaseManagerPostgreSQL database manager.
"""

import logging
from typing import Optional, Dict, Any, List
import asyncpg

logger = logging.getLogger(__name__)


class FeedbackRepository:
    """Repository methods for feedback records."""

    def __init__(self, ctx):
        """Initialize the repository with the database manager context."""
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    async def insert_feedback_records(
        self,
        session_id: str,
        review_id: str,
        field_changes: list,
        modified_by: Optional[str] = None,
    ) -> int:
        """
        Insert multiple feedback records using executemany for batch insert.

        Args:
            session_id: Session identifier
            review_id: Review identifier
            field_changes: List of FieldChangeRequest objects
            modified_by: User login who made the modification

        Returns:
            int: Number of rows inserted
        """
        try:
            query = f"""
            INSERT INTO {self.config.db_schema}.feedback_table (
                session_id,
                review_id,
                question_id,
                field_name,
                original_value,
                new_value,
                modified_by,
                modified_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP)
            """

            # Prepare batch data
            batch_data = [
                (
                    session_id,
                    review_id,
                    change.question_id,
                    change.field_name,
                    change.original_value,
                    change.new_value,
                    modified_by,
                )
                for change in field_changes
            ]

            async with self.get_connection() as conn:
                async with conn.transaction():
                    await conn.executemany(query, batch_data)

            records_inserted = len(field_changes)
            logger.info(
                "Successfully inserted %s feedback records in batch for session %s, review %s",
                records_inserted,
                session_id,
                review_id,
            )
            return records_inserted

        except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError) as e:
            logger.error(
                "Error inserting feedback records batch: %s",
                e,
                exc_info=True,
            )
            return 0

    async def get_feedback_records(self, session_id: str, review_id: str) -> List[Dict[str, Any]]:
        """
        Get all feedback records for a given session_id and review_id.

        Args:
            session_id: Session identifier
            review_id: Review identifier

        Returns:
            List of dictionaries containing feedback record fields.
        """
        try:
            query = f"""
            SELECT
                id,
                session_id,
                review_id,
                question_id,
                field_name,
                original_value,
                new_value,
                modified_by,
                modified_at
            FROM {self.config.db_schema}.feedback_table
            WHERE session_id = $1 AND review_id = $2
            ORDER BY modified_at DESC
            """

            async with self.get_connection() as conn:
                rows = await conn.fetch(query, session_id, review_id)

            if rows:
                results = []
                for row in rows:
                    result = dict(row)
                    if result.get("modified_at") and hasattr(result["modified_at"], "isoformat"):
                        result["modified_at"] = result["modified_at"].isoformat()
                    results.append(result)

                logger.info(
                    "Retrieved %s feedback record(s) for session %s, review %s",
                    len(results),
                    session_id,
                    review_id,
                )
                return results

            logger.warning(
                "No feedback records found for session %s, review %s",
                session_id,
                review_id,
            )
            return []

        except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError) as e:
            logger.error(
                "Error retrieving feedback records for session %s, review %s: %s",
                session_id,
                review_id,
                e,
                exc_info=True,
            )
            return []
