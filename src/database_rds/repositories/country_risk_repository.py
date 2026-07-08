"""Repository for country risk level lookups.

This module provides methods to check if a country belongs to
high-risk, very high-risk, or prohibited country lists used
in ODD/KYC investigations.

The data is stored in a single table: {db_schema}.lu_country_risk_classification
with columns: country, risk_classification (values: 'High Risk', 'Very High Risk', 'Prohibited')
"""

from typing import Optional, List


class CountryRiskRepository:
    """Repository methods for checking country risk levels."""

    def __init__(self, ctx):
        """Initialize the repository with the database manager context."""
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    async def is_high_risk_country(self, country: Optional[str]) -> bool:
        """
        Check if a country is in the high-risk countries list.

        Args:
            country: The country name to check (case-insensitive).

        Returns:
            True if the country is in the high_risk_countries table, False otherwise.
            Returns False if country is None or empty string.
        """
        if not country:
            return False

        query = (
            f"SELECT EXISTS("
            f"SELECT 1 FROM {self.config.db_schema}.lu_country_risk_classification "
            f"WHERE LOWER(country) = LOWER($1) "
            f"AND risk_classification = 'High Risk'"
            f")"
        )

        async with self.get_connection() as conn:
            result = await conn.fetchval(query, country.strip())
            return bool(result)

    async def is_very_high_risk_country(self, country: Optional[str]) -> bool:
        """
        Check if a country is in the very high-risk countries list.

        Args:
            country: The country name to check (case-insensitive).

        Returns:
            True if the country is in the very_high_risk_countries table, False otherwise.
            Returns False if country is None or empty string.
        """
        if not country:
            return False

        query = (
            f"SELECT EXISTS("
            f"SELECT 1 FROM {self.config.db_schema}.lu_country_risk_classification "
            f"WHERE LOWER(country) = LOWER($1) "
            f"AND risk_classification = 'Very High Risk'"
            f")"
        )

        async with self.get_connection() as conn:
            result = await conn.fetchval(query, country.strip())
            return bool(result)

    async def is_prohibited_country(self, country: Optional[str]) -> bool:
        """
        Check if a country is in the prohibited countries list.

        Args:
            country: The country name to check (case-insensitive).

        Returns:
            True if the country is in the prohibited_countries table, False otherwise.
            Returns False if country is None or empty string.
        """
        if not country:
            return False

        query = (
            f"SELECT EXISTS("
            f"SELECT 1 FROM {self.config.db_schema}.lu_country_risk_classification "
            f"WHERE LOWER(country) = LOWER($1) "
            f"AND risk_classification = 'Prohibited'"
            f")"
        )

        async with self.get_connection() as conn:
            result = await conn.fetchval(query, country.strip())
            return bool(result)

    async def get_high_risk_countries(self) -> List[str]:
        """
        Retrieve all country names from the high_risk_countries table.

        Returns:
            A list of country names.
        """
        query = (
            f"SELECT country FROM {self.config.db_schema}.lu_country_risk_classification "
            f"WHERE risk_classification = 'High Risk' "
            f"ORDER BY country"
        )

        async with self.get_connection() as conn:
            rows = await conn.fetch(query)
            return [row["country"] for row in rows]

    async def get_very_high_risk_countries(self) -> List[str]:
        """
        Retrieve all country names from the very_high_risk_countries table.

        Returns:
            A list of country names.
        """
        query = (
            f"SELECT country FROM {self.config.db_schema}.lu_country_risk_classification "
            f"WHERE risk_classification = 'Very High Risk' "
            f"ORDER BY country"
        )

        async with self.get_connection() as conn:
            rows = await conn.fetch(query)
            return [row["country"] for row in rows]

    async def get_prohibited_countries(self) -> List[str]:
        """
        Retrieve all country names from the prohibited_countries table.

        Returns:
            A list of country names.
        """
        query = (
            f"SELECT country FROM {self.config.db_schema}.lu_country_risk_classification "
            f"WHERE risk_classification = 'Prohibited' "
            f"ORDER BY country"
        )

        async with self.get_connection() as conn:
            rows = await conn.fetch(query)
            return [row["country"] for row in rows]
