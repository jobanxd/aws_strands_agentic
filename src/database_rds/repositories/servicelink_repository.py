"""
ServiceLink repository for account and transaction data.

This module contains database queries for retrieving ServiceLink
account details and transaction histories used in ODD investigations.
It also provides utilities for filtering transactions by specific
transaction codes and assembling consolidated ServiceLink data bundles.

These repository methods are integrated into the
ODDDatabaseManagerPostgreSQL manager.
"""

from typing import Optional, Dict, Any, List

from src.models.data_models import (
    ServiceLinkAccountDetails,
    ServiceLinkTransaction,
)


class ServiceLinkRepository:
    """Repository methods for ServiceLink account and transaction data."""

    def __init__(self, ctx):
        """Initialize the repository with the database manager context."""
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    async def get_servicelink_account(
        self, agmt_id: str
    ) -> Optional[ServiceLinkAccountDetails]:
        """
        Retrieve ServiceLink account details for a specific account number and NSC.

        Args:
            account_no: Account number of the ServiceLink record.
            nsc: NSC associated with the account.

        Returns:
            A ServiceLinkAccountDetails object containing the account information,
            or None if no matching record is found.
        """
        query = f"""
        SELECT *
        FROM {self.config.db_schema}.servicelink_account_details
        WHERE agmt_id = $1
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, agmt_id)
            return ServiceLinkAccountDetails(**dict(row)) if row else None

    async def get_servicelink_transactions(
        self, agmt_id: str
    ) -> List[ServiceLinkTransaction]:
        """
        Retrieve ServiceLink transaction records for a specific account.

        Args:
            account_no: Account number associated with the transactions.
            nsc: NSC associated with the account.

        Returns:
            A list of ServiceLinkTransaction objects ordered by
            transaction_date in descending order (most recent first).
        """
        query = f"""
        SELECT *
        FROM {self.config.db_schema}.servicelink_transactions
        WHERE agmt_id = $1
        AND transaction_date >= (
                SELECT MAX(transaction_date) - INTERVAL '12 months'
                FROM {self.config.db_schema}.servicelink_transactions
                WHERE agmt_id = $1
        )
        ORDER BY transaction_date DESC
        """

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, agmt_id)
            return [ServiceLinkTransaction(**dict(row)) for row in rows]

    async def get_transactions_by_codes(
        self,
        agmt_id: str,
        tx_codes: Optional[List[str]] = None,
    ) -> List[ServiceLinkTransaction]:
        """
        Get transactions filtered by specific transaction codes.
        Default codes: 931, 260, 265, 649, 769, 810
        """
        if tx_codes is None:
            tx_codes = ["931", "260", "265", "649", "769", "810"]

        query = f"""
        SELECT *
        FROM {self.config.db_schema}.servicelink_transactions
        WHERE agmt_id = $1
        AND tx_code = ANY($2)
        AND transaction_date >= (
                SELECT MAX(transaction_date) - INTERVAL '12 months'
                FROM {self.config.db_schema}.servicelink_transactions
                WHERE agmt_id = $1
        )
        ORDER BY tx_code, transaction_date DESC
        """

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, agmt_id, tx_codes)
            return [ServiceLinkTransaction(**dict(row)) for row in rows]

    async def get_servicelink_bundle(self, agmt_id: str) -> Dict[str, Any]:
        """
        Retrieve a consolidated ServiceLink data bundle for a specific account.

        This method gathers the account details, transaction history, and
        transaction code summaries for the given account number and NSC.

        Args:
            account_no: Account number associated with the ServiceLink records.
            nsc: NSC associated with the account.

        Returns:
            A dictionary containing:
                - account_details: ServiceLinkAccountDetails object
                - transactions: List of ServiceLinkTransaction objects
                - transaction_codes: Aggregated transaction code data

            Returns an empty dictionary if the account record is not found.
        """
        account = await self.get_servicelink_account(agmt_id)
        transactions = await self.get_servicelink_transactions(agmt_id)
        transaction_codes = await self.get_transactions_by_codes(agmt_id)

        if not account:
            return {}

        return {
            "account_details": account,
            "transactions": transactions,
            "transaction_codes": transaction_codes,
        }
