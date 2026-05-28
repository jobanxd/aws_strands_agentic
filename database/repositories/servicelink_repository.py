"""
ServiceLink repository for account and transaction data (SQLite version).

Provides access to ServiceLink account details and transaction history
used in ODD investigations.
"""

from typing import Optional, Dict, Any, List

from models.data_models import (
    ServiceLinkAccountDetails,
    ServiceLinkTransaction,
)


class ServiceLinkRepository:
    """SQLite repository for ServiceLink data."""

    def __init__(self, ctx):
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    # =========================
    # ACCOUNT DETAILS
    # =========================

    async def get_servicelink_account(
        self, agmt_id: str
    ) -> Optional[ServiceLinkAccountDetails]:

        query = """
        SELECT *
        FROM servicelink_account_details
        WHERE agmt_id = ?
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, (agmt_id,))
            row = await cursor.fetchone()

            return ServiceLinkAccountDetails(**dict(row)) if row else None

    # =========================
    # TRANSACTIONS (LAST 3 MONTHS)
    # =========================

    async def get_servicelink_transactions(
        self, agmt_id: str
    ) -> List[ServiceLinkTransaction]:

        query = """
        SELECT *
        FROM servicelink_transactions
        WHERE agmt_id = ?
          AND transaction_date >= (
                SELECT MAX(transaction_date) - 90
                FROM servicelink_transactions
                WHERE agmt_id = ?
          )
        ORDER BY transaction_date DESC
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, (agmt_id, agmt_id))
            rows = await cursor.fetchall()

            return [ServiceLinkTransaction(**dict(row)) for row in rows]

    # =========================
    # TRANSACTIONS BY CODE
    # =========================

    async def get_transactions_by_codes(
        self,
        agmt_id: str,
        tx_codes: Optional[List[str]] = None,
    ) -> List[ServiceLinkTransaction]:

        if tx_codes is None:
            tx_codes = ["931", "260", "265", "649", "769", "810"]

        placeholders = ",".join(["?"] * len(tx_codes))

        query = f"""
        SELECT *
        FROM servicelink_transactions
        WHERE agmt_id = ?
          AND tx_code IN ({placeholders})
          AND transaction_date >= (
                SELECT MAX(transaction_date) - 90
                FROM servicelink_transactions
                WHERE agmt_id = ?
          )
        ORDER BY tx_code, transaction_date DESC
        """

        params = [agmt_id, *tx_codes, agmt_id]

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, tuple(params))
            rows = await cursor.fetchall()

            return [ServiceLinkTransaction(**dict(row)) for row in rows]

    # =========================
    # FULL BUNDLE
    # =========================

    async def get_servicelink_bundle(self, agmt_id: str) -> Dict[str, Any]:

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
