"""
Repository for country risk level lookups (SQLite version).

This module provides methods to check if a country belongs to
high-risk, very high-risk, or prohibited country lists used
in ODD/KYC investigations.

Table: lu_country_risk_classification
Columns:
- country
- risk_classification ('High Risk', 'Very High Risk', 'Prohibited')
"""

from typing import Optional, List


class CountryRiskRepository:
    """Repository methods for checking country risk levels."""

    def __init__(self, ctx):
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    # =========================
    # HIGH RISK CHECK
    # =========================

    async def is_high_risk_country(self, country: Optional[str]) -> bool:
        if not country:
            return False

        query = """
        SELECT EXISTS(
            SELECT 1
            FROM lu_country_risk_classification
            WHERE LOWER(country) = LOWER(?)
              AND risk_classification = 'High Risk'
        )
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, (country.strip(),))
            row = await cursor.fetchone()
            return bool(row[0]) if row else False

    # =========================
    # VERY HIGH RISK CHECK
    # =========================

    async def is_very_high_risk_country(self, country: Optional[str]) -> bool:
        if not country:
            return False

        query = """
        SELECT EXISTS(
            SELECT 1
            FROM lu_country_risk_classification
            WHERE LOWER(country) = LOWER(?)
              AND risk_classification = 'Very High Risk'
        )
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, (country.strip(),))
            row = await cursor.fetchone()
            return bool(row[0]) if row else False

    # =========================
    # PROHIBITED CHECK
    # =========================

    async def is_prohibited_country(self, country: Optional[str]) -> bool:
        if not country:
            return False

        query = """
        SELECT EXISTS(
            SELECT 1
            FROM lu_country_risk_classification
            WHERE LOWER(country) = LOWER(?)
              AND risk_classification = 'Prohibited'
        )
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, (country.strip(),))
            row = await cursor.fetchone()
            return bool(row[0]) if row else False

    # =========================
    # GET HIGH RISK COUNTRIES
    # =========================

    async def get_high_risk_countries(self) -> List[str]:
        query = """
        SELECT country
        FROM lu_country_risk_classification
        WHERE risk_classification = 'High Risk'
        ORDER BY country
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query)
            rows = await cursor.fetchall()
            return [row["country"] for row in rows]

    # =========================
    # GET VERY HIGH RISK COUNTRIES
    # =========================

    async def get_very_high_risk_countries(self) -> List[str]:
        query = """
        SELECT country
        FROM lu_country_risk_classification
        WHERE risk_classification = 'Very High Risk'
        ORDER BY country
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query)
            rows = await cursor.fetchall()
            return [row["country"] for row in rows]

    # =========================
    # GET PROHIBITED COUNTRIES
    # =========================

    async def get_prohibited_countries(self) -> List[str]:
        query = """
        SELECT country
        FROM lu_country_risk_classification
        WHERE risk_classification = 'Prohibited'
        ORDER BY country
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query)
            rows = await cursor.fetchall()
            return [row["country"] for row in rows]
