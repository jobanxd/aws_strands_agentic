"""
SharePoint repository for review workflow data (SQLite version).
"""

import logging
from typing import List, Optional

from src.models.data_models import (
    SharePointListItem,
    DashboardItem,
)

logger = logging.getLogger(__name__)


class SharePointRepository:
    """Repository methods for SharePoint data."""

    def __init__(self, ctx):
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    # -----------------------------
    # Get party items
    # -----------------------------
    async def get_sharepoint_items_for_party(
        self, party_id: str
    ) -> List[SharePointListItem]:

        query = f"""
        SELECT *
        FROM sharepoint_list
        WHERE party_id = ?
        ORDER BY review_completion_date
        """

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, party_id)
            return [SharePointListItem(**dict(row)) for row in rows]

    # -----------------------------
    # Dashboard query (unchanged logic, only schema removed)
    # -----------------------------
    async def get_sharepoint_latest_items(self) -> List[DashboardItem]:

        query = """
        WITH sharepoint AS (
            SELECT
                t.*,
                ROW_NUMBER() OVER (
                    PARTITION BY party_id
                    ORDER BY
                        CASE WHEN old_review_id IS NOT NULL AND new_review_id IS NULL THEN 0 ELSE 1 END,
                        CASE WHEN next_review_date IS NULL THEN 0 ELSE 1 END DESC,
                        next_review_date DESC
                ) AS rn_latest,
                MAX(review_completion_date)
                FILTER (WHERE review_completion_date IS NOT NULL)
                OVER (
                    PARTITION BY party_id
                    ORDER BY next_review_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ) AS last_completed_review_date,
                MAX(next_review_date)
                FILTER (WHERE review_completion_date IS NOT NULL)
                OVER (
                    PARTITION BY party_id
                    ORDER BY next_review_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ) AS next_review_date_of_completed,
                MAX(CASE
                    WHEN old_review_id IS NOT NULL AND new_review_id IS NULL
                    THEN review_status
                    ELSE NULL
                END)
                OVER (PARTITION BY party_id) AS open_row_review_status
            FROM sharepoint_list t
        ),
        distinct_drilldown AS (
            SELECT DISTINCT party_id, entrp_party_ident, party_name
            FROM kycnet_drilldown
        ),
        kycnet_review_ids AS (
            SELECT
                d.party_id,
                MAX(CASE WHEN UPPER(kr.review_tag) = 'LATEST' THEN kr.review_id END) AS latest_completed_review_id,
                MAX(CASE WHEN UPPER(kr.review_tag) = 'PREVIOUS' THEN kr.review_id END) AS previous_completed_review_id
            FROM kycnet_reviews kr
            JOIN distinct_drilldown d
                ON kr.entrp_party_ident = d.entrp_party_ident
            GROUP BY d.party_id
        ),
        latest_review_risk AS (
            SELECT DISTINCT review_id,
                NULLIF(TRIM(last_manual_risk), '') AS last_manual_risk,
                NULLIF(TRIM(last_automated_risk), '') AS last_automated_risk
            FROM kycnet_drilldown
        ),
        latest_completed_report AS (
            SELECT party_id, process_id
            FROM final_report
            WHERE new_review_id <> 'FAILED'
        ),
        latest_failed_report AS (
            SELECT party_id, process_id
            FROM final_report
            WHERE new_review_id = 'FAILED'
        )

        SELECT
            s.party_id,
            d.party_name,
            kr.latest_completed_review_id,
            kr.previous_completed_review_id,
            s.review_type,
            CASE
                WHEN UPPER(s.review_status) = 'COMPLETED'
                THEN COALESCE(rr.last_manual_risk, rr.last_automated_risk)
                ELSE NULL
            END AS current_risk,
            s.next_review_date_of_completed AS next_review_date,
            s.review_completion_date,
            s.last_completed_review_date AS last_review_date,
            CASE
                WHEN UPPER(s.open_row_review_status) IN ('PROCESSING', 'NOT APPLICABLE')
                    THEN s.open_row_review_status
                WHEN s.review_status IS NULL OR s.review_status = '-'
                    THEN 'Not Started'
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
        LEFT JOIN distinct_drilldown d ON s.party_id = d.party_id
        LEFT JOIN kycnet_review_ids kr ON s.party_id = kr.party_id
        LEFT JOIN latest_review_risk rr ON kr.latest_completed_review_id = rr.review_id
        LEFT JOIN latest_completed_report fr_completed ON s.party_id = fr_completed.party_id
        LEFT JOIN latest_failed_report fr_failed ON s.party_id = fr_failed.party_id
        WHERE s.rn_latest = 1
        ORDER BY next_review_date ASC;
        """

        async with self.get_connection() as conn:
            rows = await conn.fetch(query)
            return [DashboardItem(**dict(row)) for row in rows]

    # -----------------------------
    # Latest completed
    # -----------------------------
    async def get_sharepoint_latest_completed(
        self, party_id: str
    ) -> Optional[SharePointListItem]:

        query = """
        SELECT *
        FROM sharepoint_list
        WHERE party_id = ?
          AND new_review_id <> 'NaN'
        ORDER BY review_completion_date DESC
        LIMIT 1
        OFFSET 1
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, party_id)
            return SharePointListItem(**dict(row)) if row else None

    # -----------------------------
    # Mark completed
    # -----------------------------
    async def update_review_status_completed(
        self,
        party_id: str,
        old_review_id: str,
        new_review_id: str,
    ) -> bool:

        query = """
        UPDATE sharepoint_list
        SET review_status = 'Completed',
            review_completion_date = CURRENT_DATE,
            next_review_date = date('now', '+12 months'),
            review_type = 'Periodic/Trigger Review (Personal)',
            new_review_id = ?
        WHERE party_id = ?
          AND old_review_id = ?
        """

        async with self.get_connection() as conn:
            result = await conn.execute(query, new_review_id, party_id, old_review_id)

            # SQLite-friendly: cannot rely on "rows affected string"
            return True if result else False

    # -----------------------------
    # Update status
    # -----------------------------
    async def update_review_status(
        self,
        party_id: str,
        review_id: Optional[str] = None,
        status: str = "Processing",
    ) -> bool:

        if review_id:
            query = """
            UPDATE sharepoint_list
            SET review_status = ?
            WHERE party_id = ?
              AND old_review_id = ?
              AND (UPPER(review_status) != 'COMPLETED' OR review_status IS NULL)
            """
            params = (status, party_id, review_id)
        else:
            query = """
            UPDATE sharepoint_list
            SET review_status = ?
            WHERE party_id = ?
              AND review_completion_date IS NULL
            """
            params = (status, party_id)

        async with self.get_connection() as conn:
            result = await conn.execute(query, *params)
            return True if result else False