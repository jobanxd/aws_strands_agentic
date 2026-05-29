"""
KYC data repository for ODD investigations (SQLite version).
"""

from typing import Optional, List

from src.models.data_models import (
    PartyInfo,
    ReviewInfo,
    SvoCExtract,
)


class KYCRepository:
    """Repository methods for KYC and SVoC data."""

    def __init__(self, ctx):
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    # =========================
    # PARTY INFO
    # =========================

    async def get_party_info(self, party_id: str) -> List[PartyInfo]:
        query = """
        SELECT *
        FROM kycnet_drilldown
        WHERE party_id = ?
        ORDER BY date_current_review_started DESC
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, (party_id,))
            rows = await cursor.fetchall()

            return [PartyInfo(**dict(row)) for row in rows]

    # =========================
    # REVIEW INFO
    # =========================

    async def get_review_info(self, review_id: str) -> Optional[ReviewInfo]:
        query = """
        SELECT *
        FROM kycnet_reviews
        WHERE review_id = ?
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, (review_id,))
            row = await cursor.fetchone()

            return ReviewInfo(**dict(row)) if row else None

    # =========================
    # SVoC EXTRACT
    # =========================

    async def get_svoc_extract(
        self,
        entrp_party_ident: Optional[str] = None,
    ) -> List[SvoCExtract]:
        query = """
        SELECT *
        FROM svoc_extracts
        WHERE entrp_party_ident = ?
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, (entrp_party_ident,))
            rows = await cursor.fetchall()

            return [SvoCExtract(**dict(row)) for row in rows]
