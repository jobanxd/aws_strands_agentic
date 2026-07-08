"""
SharePoint repository for review workflow data.

This module provides database operations for accessing SharePoint
review records used in the ODD process, including retrieving
historical reviews, latest review entries, and completed review
information for specific parties.

The methods defined here are used by agent workflows and dashboard
features through the ODDDatabaseManagerPostgreSQL manager.
"""

import logging
from typing import List, Optional
import asyncpg

from src.models.data_models import (
    SharePointListItem,
    DashboardItem,
)

logger = logging.getLogger(__name__)


class SharePointRepository:
    """Repository methods for SharePoint data."""

    def __init__(self, ctx):
        """Initialize the repository with the database manager context."""
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    async def get_sharepoint_items_for_party(self, party_id: str) -> List[SharePointListItem]:
        """
        Retrieve SharePoint list records associated with a specific party.

        Args:
            party_id: Unique identifier of the party whose SharePoint records
                should be retrieved.

        Returns:
            A list of SharePointListItem objects ordered by review_completion_date.
        """
        query = f"""
        SELECT *
        FROM {self.config.db_schema}.sharepoint_list
        WHERE party_id = $1
        ORDER BY review_completion_date
        """

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, party_id)
            return [SharePointListItem(**dict(row)) for row in rows]

    async def get_sharepoint_latest_items(self) -> List[DashboardItem]:
        """
        Retrieve the latest SharePoint list entry per party for dashboard display.

        For each party_id, selects the most recent record by next_review_date and
        enriches it with party metadata from kycnet_drilldown. Also computes the
        last completed review date and the next_review_date of the last completed
        review using window functions.

        Returns:
            A list of DashboardItem objects ordered by next_review_date ascending.
        """
        query = f"""
        WITH sharepoint AS (
            SELECT
                t.*,
                ROW_NUMBER() OVER (
                    PARTITION BY party_id
                    ORDER BY
                        -- Active/in-progress row first (has old_review_id but no new_review_id yet)
                        CASE WHEN old_review_id IS NOT NULL AND new_review_id IS NULL THEN 0 ELSE 1 END,
                        -- Then prefer rows with next_review_date
                        CASE WHEN next_review_date IS NULL THEN 0 ELSE 1 END DESC,
                        next_review_date DESC NULLS LAST
                ) AS rn_latest,
                MAX(review_completion_date) FILTER (WHERE review_completion_date IS NOT NULL)
                OVER (
                    PARTITION BY party_id
                    ORDER BY next_review_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ) AS last_completed_review_date,
                MAX(next_review_date) FILTER (WHERE review_completion_date IS NOT NULL)
                OVER (
                    PARTITION BY party_id
                    ORDER BY next_review_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ) AS next_review_date_of_completed,
                -- Only treat truly active rows (no new_review_id yet) as open
                MAX(CASE
                    WHEN old_review_id IS NOT NULL AND new_review_id IS NULL
                    THEN review_status
                    ELSE NULL
                END)
                OVER (PARTITION BY party_id) AS open_row_review_status
            FROM {self.config.db_schema}.sharepoint_list t
        ),
        distinct_drilldown AS (
            -- DISTINCT ON party_id to avoid duplicates from name spelling differences
            SELECT DISTINCT ON (party_id)
                party_id,
                entrp_party_ident,
                party_name
            FROM {self.config.db_schema}.kycnet_drilldown
            ORDER BY party_id, party_name
        ),
        -- Use kycnet_reviews + kycnet_drilldown to resolve latest/previous review IDs
        kycnet_review_ids AS (
            SELECT
                d.party_id,
                MAX(CASE WHEN UPPER(kr.review_tag) = 'LATEST'   THEN kr.review_id END) AS latest_completed_review_id,
                MAX(CASE WHEN UPPER(kr.review_tag) = 'PREVIOUS' THEN kr.review_id END) AS previous_completed_review_id
            FROM {self.config.db_schema}.kycnet_reviews kr
            JOIN distinct_drilldown d
                ON kr.entrp_party_ident = d.entrp_party_ident
            GROUP BY d.party_id
        ),
        -- Get risk fields from kycnet_drilldown for the latest completed review ID
        latest_review_risk AS (
            SELECT DISTINCT ON (kd.review_id)
                kd.review_id,
                NULLIF(TRIM(kd.last_manual_risk), '')   AS last_manual_risk,
                NULLIF(TRIM(kd.last_automated_risk), '') AS last_automated_risk
            FROM {self.config.db_schema}.kycnet_drilldown kd
            ORDER BY kd.review_id
        ),
        latest_completed_report AS (
            SELECT DISTINCT ON (party_id)
                party_id,
                process_id
            FROM {self.config.db_schema}.final_report
            WHERE new_review_id <> 'FAILED'
            ORDER BY party_id, created_at DESC
        ),
        latest_failed_report AS (
            SELECT DISTINCT ON (party_id)
                party_id,
                process_id
            FROM {self.config.db_schema}.final_report
            WHERE new_review_id = 'FAILED'
            ORDER BY party_id, created_at DESC
        )

        SELECT
            s.party_id,
            d.party_name,
            kr.latest_completed_review_id,
            kr.previous_completed_review_id,
            s.review_type,
            -- Use last_manual_risk first, fall back to last_automated_risk
            -- Only populate when Completed, otherwise NULL
            CASE
                WHEN UPPER(s.review_status) = 'COMPLETED'
                THEN COALESCE(rr.last_manual_risk, rr.last_automated_risk)
                ELSE NULL
            END AS current_risk,
            s.next_review_date_of_completed AS next_review_date,
            s.review_completion_date,
            s.last_completed_review_date AS last_review_date,
            CASE
                WHEN UPPER(s.open_row_review_status) IN ('PROCESSING', 'NOT APPLICABLE') THEN s.open_row_review_status
                WHEN s.review_status IS NULL OR s.review_status = '-' THEN 'Not Started'
                ELSE s.review_status
            END AS review_status,
            CASE
                WHEN UPPER(s.open_row_review_status) = 'NOT APPLICABLE' THEN fr_failed.process_id
                WHEN s.review_status IS NULL OR s.review_status = '-' THEN NULL
                WHEN UPPER(s.open_row_review_status) = 'PROCESSING' THEN NULL
                WHEN UPPER(s.review_status) = 'COMPLETED' THEN fr_completed.process_id
                ELSE NULL
            END AS process_id
        FROM sharepoint s
        LEFT JOIN distinct_drilldown d
            ON s.party_id = d.party_id
        LEFT JOIN kycnet_review_ids kr
            ON s.party_id = kr.party_id
        -- Join risk data using the latest completed review ID
        LEFT JOIN latest_review_risk rr
            ON kr.latest_completed_review_id = rr.review_id
        LEFT JOIN latest_completed_report fr_completed
            ON s.party_id = fr_completed.party_id
        LEFT JOIN latest_failed_report fr_failed
            ON s.party_id = fr_failed.party_id
        WHERE s.rn_latest = 1
        ORDER BY next_review_date ASC;
        """

        async with self.get_connection() as conn:
            rows = await conn.fetch(query)
            return [DashboardItem(**dict(row)) for row in rows]

    async def get_sharepoint_latest_completed(self, party_id: str) -> SharePointListItem:
        """
        Retrieve the most recent completed SharePoint review record for a given party.

        Args:
            party_id: Unique identifier of the party.

        Returns:
            A SharePointListItem representing the latest completed review,
            or None if no completed review exists for the party.
        """
        query = f"""
        SELECT *
        FROM {self.config.db_schema}.sharepoint_list
        WHERE party_id = $1 and new_review_id <> 'NaN'
        ORDER BY review_completion_date desc
        LIMIT 1
        OFFSET 1
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, party_id)
            return SharePointListItem(**dict(row)) if row else None

    async def update_review_status_completed(
        self, party_id: str, old_review_id: str, new_review_id: str
    ) -> bool:
        """
        Update the review status to 'Completed' for a specific party and review.

        Args:
            party_id: Unique identifier of the party.
            old_review_id: The old review ID to match.
            new_review_id: The new review ID to set.

        Returns:
            True if a row was updated, False otherwise.
        """
        query = f"""
        UPDATE {self.config.db_schema}.sharepoint_list
        SET review_status = 'Completed',
            review_completion_date = CURRENT_DATE,
            next_review_date = CURRENT_DATE + INTERVAL '12 months',
            review_type = 'Periodic/Trigger Review (Personal)',
            new_review_id = $3
        WHERE party_id = $1 AND old_review_id = $2
        """

        try:
            async with self.get_connection() as conn:
                result = await conn.execute(query, party_id, old_review_id, new_review_id)

                # Check if any rows were affected
                if result and result.split()[-1] != '0':
                    logger.info(
                        "Updated review status for party %s, review_id - old: %s -> new: %s",
                        party_id,
                        old_review_id,
                        new_review_id,
                    )
                    return True

                logger.warning(
                    "No matching record found for party %s, review %s",
                    party_id,
                    old_review_id,
                )
                return False

        except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError) as e:
            logger.error(
                "Error updating review status for party %s, review %s: %s",
                party_id,
                old_review_id,
                e,
                exc_info=True,
            )
            return False

    async def update_review_status(
        self, party_id: str, review_id: Optional[str] = None, status: str = 'Processing'
    ) -> bool:
        """
        Update the review status to 'Pending' for a specific party and review,
        but only if the current status is not 'Completed'.

        Args:
            party_id: Unique identifier of the party.
            review_id: The review ID to match (old_review_id column).

        Returns:
            True if a row was updated, False otherwise.
        """
        if review_id:
            query = f"""
            UPDATE {self.config.db_schema}.sharepoint_list
            SET review_status = $1
            WHERE party_id = $2
            AND old_review_id = $3
            AND (UPPER(review_status) != 'COMPLETED' OR review_status IS NULL)
            """
        else:
            query = f"""
            UPDATE {self.config.db_schema}.sharepoint_list
            SET review_status = $1
            WHERE party_id = $2
            AND review_completion_date is NULL
            """

        try:
            async with self.get_connection() as conn:
                if review_id:
                    result = await conn.execute(query, status, party_id, review_id)
                else:
                    result = await conn.execute(query, status, party_id)

                # Check if any rows were affected
                if result and result.split()[-1] != '0':
                    logger.info(
                        "Review status updated %s for party %s, review_id %s",
                        status,
                        party_id,
                        review_id,
                    )
                    return True

                logger.debug(
                    "No rows updated for party %s, review_id %s",
                    party_id,
                    review_id,
                )
                return False

        except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError) as e:
            logger.error(
                "Error updating review status to Pending for party %s, review %s: %s",
                party_id,
                review_id,
                e,
                exc_info=True,
            )
            return False
