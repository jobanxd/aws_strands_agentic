"""
Feedback repository for final report corrections (SQLite version).

This module stores and retrieves feedback records for KYC final reports,
tracking field-level changes (original → updated values).
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class FeedbackRepository:
    """SQLite repository for feedback records."""

    def __init__(self, ctx):
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    # =========================
    # INSERT FEEDBACK (BATCH)
    # =========================

    async def insert_feedback_records(
        self,
        session_id: str,
        review_id: str,
        field_changes: list,
        modified_by: Optional[str] = None,
    ) -> int:
        try:
            query = """
            INSERT INTO feedback_table (
                session_id,
                review_id,
                question_id,
                field_name,
                original_value,
                new_value,
                modified_by,
                modified_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """

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
                    await conn.commit()

            logger.info(
                "Inserted %s feedback records for session %s, review %s",
                len(field_changes),
                session_id,
                review_id,
            )

            return len(field_changes)

        except Exception as e:
            logger.error("Error inserting feedback records: %s", e, exc_info=True)
            return 0

    # =========================
    # GET FEEDBACK RECORDS
    # =========================

    async def get_feedback_records(
        self,
        session_id: str,
        review_id: str,
    ) -> List[Dict[str, Any]]:

        query = """
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
        FROM feedback_table
        WHERE session_id = ? AND review_id = ?
        ORDER BY modified_at DESC
        """

        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(query, (session_id, review_id))
                rows = await cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)

                # SQLite returns datetime as-is (no need for isoformat conversion usually)
                if isinstance(result.get("modified_at"), str):
                    result["modified_at"] = result["modified_at"]

                results.append(result)

            if results:
                logger.info(
                    "Retrieved %s feedback records for session %s, review %s",
                    len(results),
                    session_id,
                    review_id,
                )
            else:
                logger.warning(
                    "No feedback records found for session %s, review %s",
                    session_id,
                    review_id,
                )

            return results

        except Exception as e:
            logger.error(
                "Error retrieving feedback records: %s",
                e,
                exc_info=True,
            )
            return []
