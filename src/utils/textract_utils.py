"""
Builds structured KYC data (passport / proof of ID / employment / proof of
address) from documents that were already run through Textract by the
pre-processing lambda and cached in RDS (`textract_extracted_documents`).

This file used to own the S3 listing, variant matching, and Textract calls
itself (see TextractManager in the old version). All of that now happens
in the pre-processing lambda - this file only reads the cached content and
runs it through the same extraction prompts/models as before.

No S3 client, no presigned URLs, no messaging/websocket notifications:
- document_path on each result is now just the raw S3 key (file_key) the
  content came from, not a fetchable URL, so downstream steps still know
  exactly which source document fed each field - useful when archiving
  processed documents to S3 later.
"""

import asyncio
import json
import logging
import os

from strands import Agent
from pydantic import ValidationError

from src.core.model_factory import get_model
from src.database_rds.rds_postgres_manager import ODDDatabaseManagerPostgreSQL
from src.models.data_models import (
    ProofOfIDData,
    EmploymentData,
    ProofOfAddressData,
)
from src.models.agent_models import TextractData

logger = logging.getLogger(__name__)

TEXTRACT_CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "70.0"))

agent = Agent(
    model=get_model()
)

class TextractManager:
    """Builds structured KYC data from pre-extracted Textract content in RDS."""

    _PROMPT_INDEX = {
        "passport": 2.0,
        "proof_of_id": 3.0,
        "employment": 4.0,
        "proof_of_address": 5.0,
    }
    _MODEL_CLASS = {
        "passport": ProofOfIDData,
        "proof_of_id": ProofOfIDData,
        "employment": EmploymentData,
        "proof_of_address": ProofOfAddressData,
    }

    async def _process_cached_document(
        self,
        document_type: str,
        cached: dict,
        party_id: str,
        review_id: str,
        db: "ODDDatabaseManagerPostgreSQL",
    ):
        """
        Run the existing extraction prompt/model against content that was
        already extracted by Textract in the pre-processing lambda, instead
        of calling Textract here.
        """
        content = cached.get("content")
        if not content:
            logger.warning("No cached content for %s (party_id=%s)", document_type, party_id)
            return None

        prompt_template = await db.agent.get_agent_prompt(self._PROMPT_INDEX[document_type])
        if not prompt_template:
            raise ValueError(f"Extract {document_type} data prompt not found in database")

        prompt = prompt_template.format(
            party_id=party_id,
            review_id=review_id,
            text=content,
            confidence_threshold=TEXTRACT_CONFIDENCE_THRESHOLD,
        )

        try:
            response = Agent(prompt)
            data = json.loads(response)
            document_data = self._MODEL_CLASS[document_type](**data)

            # document_path is now just the S3 key, not a fetchable URL - kept
            # so downstream steps know which file this data came from when
            # archiving processed documents to S3.
            document_data.document_path = cached["file_key"]

            logger.info("Successfully built %s data from cached extraction", document_type)
            return document_data

        except json.JSONDecodeError as e:
            logger.error("%s LLM extraction failed - invalid JSON: %s", document_type, e)
            return None

        except ValidationError as e:
            logger.error(
                "%s LLM extraction failed - schema validation error: %s", document_type, e
            )
            return None

    async def extract_party_documents(
        self,
        party_id: str,
        review_id: str,
        db: "ODDDatabaseManagerPostgreSQL",
    ) -> "TextractData":
        """
        Build structured KYC data for a party from documents that were
        already run through Textract by the pre-processing lambda.

        No S3 listing, no Textract calls, no review_id fallback - reads
        exactly what's cached in RDS for this party_id/review_id.
        """
        cached_docs = await db.textract.get_extracted_documents(party_id, review_id)

        if not cached_docs:
            logger.warning(
                "No pre-processed documents found for party_id=%s review_id=%s",
                party_id,
                review_id,
            )
            return TextractData(
                party_id=party_id,
                review_id=review_id,
                proof_of_id=None,
                employment=None,
                proof_of_address=None,
            )

        # Passport wins if present, otherwise fall back to the generic
        # proof_of_id document.
        id_doc_type = "passport" if "passport" in cached_docs else (
            "proof_of_id" if "proof_of_id" in cached_docs else None
        )

        coros = {}
        if id_doc_type:
            coros["proof_of_id"] = self._process_cached_document(
                id_doc_type, cached_docs[id_doc_type], party_id, review_id, db
            )
        if "employment" in cached_docs:
            coros["employment"] = self._process_cached_document(
                "employment", cached_docs["employment"], party_id, review_id, db
            )
        if "proof_of_address" in cached_docs:
            coros["proof_of_address"] = self._process_cached_document(
                "proof_of_address", cached_docs["proof_of_address"], party_id, review_id, db
            )

        results = await asyncio.gather(*coros.values(), return_exceptions=True)
        resolved = dict(zip(coros.keys(), results))

        for key, value in resolved.items():
            if isinstance(value, Exception):
                logger.error("%s extraction failed: %s", key, value)
                resolved[key] = None

        return TextractData(
            party_id=party_id,
            review_id=review_id,
            proof_of_id=resolved.get("proof_of_id"),
            employment=resolved.get("employment"),
            proof_of_address=resolved.get("proof_of_address"),
        )