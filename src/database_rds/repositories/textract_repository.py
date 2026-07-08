"""Repository for reading pre-processed Textract extraction results.

This module provides read access to the textract_extracted_documents
table, populated by the pre-processing lambda that runs documents through
AWS Textract ahead of the ODD run. This repository does not run Textract
or the LLM itself - it only reads what's already been extracted.

The data is stored in a single table: {db_schema}.textract_extracted_documents
with columns: party_id, review_id, document_type, original_suffix, file_key,
file_type, content, avg_confidence, status, error_message, created_at, updated_at
"""

from typing import Dict


class TextractRepository:
    """Repository methods for reading pre-processed Textract extraction results."""

    def __init__(self, ctx):
        """Initialize the repository with the database manager context."""
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    async def get_extracted_documents(self, party_id: str, review_id: str) -> Dict[str, dict]:
        """
        Retrieve all pre-processed documents for a party/review.

        Args:
            party_id: The party ID to look up.
            review_id: The review ID to look up.

        Returns:
            A dict of {document_type: {content, avg_confidence, file_key}}
            for every document pre-processed for this party_id/review_id.
            Only rows with status = 'completed' are included - failed
            extractions are skipped, so callers naturally treat that
            document type as missing.
        """
        query = (
            f"SELECT document_type, content, avg_confidence, file_key "
            f"FROM {self.config.db_schema}.textract_extracted_documents "
            f"WHERE party_id = $1 AND review_id = $2 "
            f"AND status = 'completed'"
        )

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, party_id.strip(), review_id.strip())
            return {
                row["document_type"]: {
                    "content": row["content"],
                    "avg_confidence": row["avg_confidence"],
                    "file_key": row["file_key"],
                }
                for row in rows
            }