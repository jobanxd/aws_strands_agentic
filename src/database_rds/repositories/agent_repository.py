"""
Agent repository for ODD/KYC workflow persistence.

This module contains database access methods related to agent operations,
including storing agent outputs, retrieving agent summaries, recording
agent failures, managing agent prompts, and logging agent messages.

These methods are intended to be used through the
ODDDatabaseManagerPostgreSQL class, which provides the database
connection and configuration context.
"""

import os
import json
import logging
import uuid
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import asyncpg

from src.models.agent_models import (
    AgentOutputParams,
    AgentFailureParams,
    AgentMessageParams,
    AgentTokenUsageParams,
)

load_dotenv()
logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("LLM_MODEL")


class AgentRepository:
    """Repository methods for agent outputs, failures, prompts, and messages."""

    def __init__(self, ctx):
        """Initialize the repository with the database manager context."""
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    async def save_agent_output(
        self,
        params: Optional[AgentOutputParams] = None,
        **kwargs,
    ) -> None:
        """Insert or update an agent output record."""
        if params is None and not kwargs:
            raise ValueError("Either params or keyword arguments must be provided.")

        if params is None:
            params = AgentOutputParams(**kwargs)

        query = f"""
        INSERT INTO {self.config.db_schema}.agent_outputs (
            agent_name,
            session_id,
            process_id,
            output_json,
            summary,
            updated_at
        )
        VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
        ON CONFLICT (agent_name, session_id, process_id)
        DO UPDATE SET
            output_json = EXCLUDED.output_json,
            summary = EXCLUDED.summary,
            updated_at = CURRENT_TIMESTAMP
        """

        payload_json = params.output.model_dump_json()

        async with self.get_connection() as conn:
            await conn.execute(
                query,
                params.agent_name,
                params.session_id,
                params.process_id,
                payload_json,
                params.summary,
            )

    async def get_agent_output(
        self, agent_name: str, process_id: str, output_model=None, session_id: Optional[str] = None
    ):
        """
        Retrieve agent output from database.

        Args:
            agent_name: Name of the agent
            session_id: Session identifier
            process_id: Process identifier
            output_model: Optional Pydantic model class to validate against.
                         If None, returns raw dict.

        Returns:
            Validated model instance if output_model provided, otherwise dict
        """
        conditions = ["agent_name = $1", "process_id = $2"]
        args = [agent_name, process_id]

        if session_id is not None:
            conditions.append(f"session_id = ${len(args) + 1}")
            args.append(session_id)

        query = f"""
        SELECT output_json
        FROM {self.config.db_schema}.agent_outputs
        WHERE {" AND ".join(conditions)}
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, *args)
            if not row:
                return None

            # If output_model is provided, validate and return model instance
            if output_model:
                return output_model.model_validate_json(row["output_json"])

            # Otherwise return raw dict
            return json.loads(row["output_json"])

    async def get_agent_failure(self, process_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve agent failure information from database.

        Args:
            process_id: Process identifier

        Returns:
            Dictionary containing failure information or None if not found
        """
        query = f"""
        SELECT
            id,
            agent_name,
            session_id,
            process_id,
            reason,
            recommendation,
            created_at
        FROM {self.config.db_schema}.agent_failures
        WHERE process_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """

        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, process_id)
            if not row:
                return None

            return {
                "id": row["id"],
                "agent_name": row["agent_name"],
                "session_id": row["session_id"],
                "process_id": row["process_id"],
                "reason": row["reason"],
                "recommendation": row["recommendation"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }

    async def save_agent_failure(
        self,
        params: Optional[AgentFailureParams] = None,
        **kwargs,
    ) -> None:
        """
        Save agent failure information to database.
        Also saves to final_report table with reason
        in overview_summary and recommendation in next_steps.
        All other fields in final_report will be NULL.

        Args:
            agent_name: Name of the agent that encountered the failure
            session_id: Session identifier
            process_id: Process identifier
            reason: Detailed reason for the failure (will be saved to overview_summary)
            recommendation: Recommendation to resolve the failure (will be saved to next_steps)
            party_id: Optional party identifier.
                If not provided, will attempt to retrieve from Data Analyst output
        """
        if params is None and not kwargs:
            raise ValueError("Either params or keyword arguments must be provided.")

        if params is None:
            params = AgentFailureParams(**kwargs)

        # Save to agent_failures table
        query = f"""
        INSERT INTO {self.config.db_schema}.agent_failures (
            agent_name,
            session_id,
            process_id,
            reason,
            recommendation,
            created_at
        )
        VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
        ON CONFLICT (session_id, process_id)
        DO UPDATE SET
            agent_name = EXCLUDED.agent_name,
            reason = EXCLUDED.reason,
            recommendation = EXCLUDED.recommendation,
            created_at = CURRENT_TIMESTAMP
        """

        async with self.get_connection() as conn:
            await conn.execute(
                query,
                params.agent_name,
                params.session_id,
                params.process_id,
                params.reason,
                params.recommendation,
            )

        logger.info(
            "Saved failure for agent '%s' in session %s, process %s",
            params.agent_name,
            params.session_id,
            params.process_id,
        )

        # Also save to final_report table with failure information
        try:
            party_id = params.party_id

            # Attempt to derive party_id from Data Analyst output
            if not party_id:
                try:
                    da_output = await self.get_agent_output(
                        agent_name="Data Analyst",
                        session_id=params.session_id,
                        process_id=params.process_id,
                        output_model=None,  # Get as dict
                    )
                    if da_output:
                        party_id = da_output.get("party_info", {}).get("party_id")
                except (AttributeError, KeyError, TypeError, ValueError) as e:
                    logger.debug(
                        "Could not retrieve party_id from Data Analyst output: %s",
                        e,
                    )

            # Only save to final_report if we have a party_id
            if party_id:
                # Insert directly into final_report with only the failure information
                # All KYC form fields will be NULL
                query = f"""
                INSERT INTO {self.config.db_schema}.final_report (
                    party_id,
                    new_review_id,
                    session_id,
                    process_id,
                    overview_summary,
                    next_steps,
                    created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                """

                async with self.get_connection() as conn:
                    await conn.execute(
                        query,
                        party_id,
                        "FAILED",  # Indicate this is a failure report
                        params.session_id,
                        params.process_id,
                        params.reason,  # Save reason directly to overview_summary
                        params.recommendation,  # Save recommendation directly to next_steps
                    )

                logger.info("Failure also saved to final_report table for party_id=%s", party_id)
            else:
                logger.debug("No party_id available, skipping final_report save for failure")

        except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError) as e:
            logger.error(
                "Error saving failure to final_report table: %s",
                e,
                exc_info=True,
            )

    async def get_all_agent_summaries(
        self, session_id: str, process_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all agent summaries for a given session and process.
        Now retrieves summaries from agent_outputs table instead of agent_summaries.

        Args:
            session_id: Session identifier
            process_id: Process identifier

        Returns:
            List of summary dictionaries with agent_name and summary_text
        """
        query = f"""
        SELECT agent_name, summary, updated_at
        FROM {self.config.db_schema}.agent_outputs
        WHERE session_id = $1 AND process_id = $2 AND summary IS NOT NULL
        ORDER BY updated_at ASC
        """

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, session_id, process_id)
            results = []
            for row in rows:
                results.append(
                    {
                        "agent_name": row["agent_name"],
                        "summary_text": row["summary"],
                        "updated_at": row["updated_at"],
                    }
                )
            return results

    async def get_agent_prompt(
        self, prompt_index: float, model_name: str = LLM_MODEL
    ) -> Optional[str]:
        """
        Get an agent prompt from the database by prompt_index and model_name.
        Retrieves the latest version based on the base index.

        Args:
            prompt_index: The base prompt index (e.g., 1.0, 2.0, 3.0)
            model_name: The model name to filter prompts

        Returns:
            The prompt content as a string, or None if not found.
        """
        try:
            async with self.get_connection() as conn:
                base_index = int(prompt_index)

                query = f"""
                    SELECT prompt_content, prompt_index, agent_name, model_name
                    FROM {self.config.db_schema}.lu_agent_prompts
                    WHERE prompt_index >= $1
                    AND prompt_index < $2
                    AND model_name = $3
                    ORDER BY prompt_index DESC
                    LIMIT 1
                """

                row = await conn.fetchrow(
                    query, float(base_index), float(base_index + 1), model_name
                )

            if row:
                logger.info(
                    "Retrieved prompt for %s using index %s and model %s",
                    row["agent_name"],
                    row["prompt_index"],
                    row["model_name"],
                )
                return row["prompt_content"]

            logger.warning(
                "Prompt not found for prompt_index=%s and model_name=%s",
                prompt_index,
                model_name,
            )
            return None

        except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError) as e:
            logger.error(
                "Error retrieving agent prompt with index %s and model %s: %s",
                prompt_index,
                model_name,
                e,
                exc_info=True,
            )
            return None

    async def log_agent_message(
        self,
        params: Optional[AgentMessageParams] = None,
        **kwargs,
    ) -> bool:
        """
        Log agent message to PostgreSQL with optional project and user identifiers.

        Args:
            session_id: Session identifier
            process_id: Process identifier
            payload: Message payload as dictionary
            project_id: Optional project identifier
            user_id: Optional user identifier

        Returns:
            bool: True if successful, False otherwise
        """
        if params is None and not kwargs:
            raise ValueError("Either params or keyword arguments must be provided.")

        if params is None:
            params = AgentMessageParams(**kwargs)

        try:
            # Generate a unique ID for this message
            message_id = str(uuid.uuid4())

            # Convert payload to JSON string
            payload_json = json.dumps(params.payload)

            logger.debug(
                f"DB INSERT [agent_messages] PAYLOAD: {payload_json[:500]}..."
                if len(payload_json) > 500
                else f"DB INSERT [agent_messages] PAYLOAD: {payload_json}"
            )

            query = f"""
            INSERT INTO {self.config.db_schema}.agent_messages (
                id,
                session_id,
                process_id,
                payload,
                project_id,
                user_id
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            """

            async with self.get_connection() as conn:
                await conn.execute(
                    query,
                    message_id,
                    params.session_id,
                    params.process_id,
                    payload_json,
                    params.project_id,
                    params.user_id,
                )

            return True

        except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError) as e:
            logger.error(
                "FAILED TO INSERT AGENT MESSAGE - Database Write Error: %s",
                e,
                exc_info=True,
            )
            logger.error("Database may be READ-ONLY or connection failed")
            logger.error(
                "Agent messages WILL NOT be saved for session: %s",
                params.session_id,
            )
            return False

    async def get_agent_messages(self, process_id: str) -> List[Dict[str, Any]]:
        """
        Get agent messages from PostgreSQL.

        Args:
            session_id: Session identifier
            process_id: Process identifier
            project_id: Optional project identifier

        Returns:
            List of message dictionaries with payload and timestamp.
        """
        try:
            query = f"""
            SELECT payload, created_at
            FROM {self.config.db_schema}.agent_messages
            WHERE process_id = $1
            ORDER BY created_at ASC
            """

            async with self.get_connection() as conn:
                rows = await conn.fetch(query, process_id)

            messages = []
            for row in rows:
                # Parse the JSON payload
                payload_obj = json.loads(row["payload"])
                # Add timestamp to the payload object
                payload_obj["timestamp"] = row["created_at"]
                messages.append(payload_obj)

            return messages

        except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError) as e:
            logger.error(
                "Error getting agent messages for process %s: %s",
                process_id,
                e,
                exc_info=True,
            )
            return []

    async def save_agent_token_usage(
        self,
        params: Optional[AgentTokenUsageParams] = None,
        **kwargs,
    ) -> None:
        """Saving agent token usage to DB"""

        if params is None and not kwargs:
            raise ValueError("Either params or keyword arguments must be provided.")

        if params is None:
            params = AgentTokenUsageParams(**kwargs)

        try:
            query = f"""
            INSERT INTO {self.config.db_schema}.agent_token_usage
                (process_id, agent_name, input_tokens, output_tokens, total_tokens, response_preview)
            VALUES
                ($1, $2, $3, $4, $5, $6)
            """
            total = (params.input_tokens or 0) + (params.output_tokens or 0)

            async with self.get_connection() as conn:
                await conn.execute(
                    query,
                    params.process_id,
                    params.agent_name,
                    params.input_tokens,
                    params.output_tokens,
                    total,
                    params.response_preview,
                )
        except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError) as e:
            logger.error(
                "Error saving agent token usage for process %s: %s",
                params.process_id, e, exc_info=True
            )
