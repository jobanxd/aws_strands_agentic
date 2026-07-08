"""
KYC data repository for ODD investigations.

This module provides database access methods for retrieving
Know Your Customer (KYC) data used during ODD investigations,
including party information, review records, and SVoC extracts.

These methods support agent workflows that analyze customer
profiles and historical review data.
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
        """Initialize the repository with the database manager context."""
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    async def get_party_info(self, party_id: str) -> List[PartyInfo]:
        """
        Retrieve KYC drilldown records for a specific party.

        Args:
            party_id: Unique identifier of the party.

        Returns:
            A list of PartyInfo objects ordered by the most recent
            review start date in descending order.
        """
        query = f"""
        SELECT *
        FROM {self.config.db_schema}.kycnet_drilldown
        WHERE party_id = $1
        ORDER BY date_current_review_started DESC
        """

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, party_id)
            return [PartyInfo(**dict(row)) for row in rows]

    async def get_review_info(self, review_id: str) -> Optional[ReviewInfo]:
        """
        Retrieve review details for a specific review ID.

        Args:
            review_id: Unique identifier of the review.

        Returns:
            A ReviewInfo object containing the review details, or None
            if the review record is not found.
        """
        query = f"""
        SELECT *
        FROM {self.config.db_schema}.kycnet_reviews
        WHERE review_id = $1
        """
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, review_id)
            return ReviewInfo(**dict(row)) if row else None

    async def get_svoc_extract(
        self,
        entrp_party_ident: Optional[str] = None,
    ) -> List[SvoCExtract]:
        """
        Retrieve SVoC extract records filtered by optional search criteria.

        Args:
            name: Partial or full name to match (case-insensitive).
            dob: Exact date of birth to filter records.
            address_keyword: Keyword to match within the address field
                (case-insensitive).

        Returns:
            A list of SvoCExtract objects matching the provided filters.
            If no filters are provided, all records are returned.
        """

        query = f"""
        SELECT *
        FROM {self.config.db_schema}.svoc_extracts
        WHERE entrp_party_ident = $1
        """

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, entrp_party_ident)
            return [SvoCExtract(**dict(row)) for row in rows]
