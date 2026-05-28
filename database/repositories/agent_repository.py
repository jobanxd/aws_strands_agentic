"""
Agent repository for ODD/KYC workflow persistence (SQLite version).
"""

import os
import json
import logging
import uuid
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv

from models.agent_models import (
    AgentOutputParams,
    AgentFailureParams,
    AgentMessageParams,
    AgentTokenUsageParams,
)

load_dotenv()
logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("LLM_MODEL")


class AgentRepository:
    """SQLite repository for agent operations."""

    def __init__(self, ctx):
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    # =========================
    # AGENT OUTPUT
    # =========================

    async def save_agent_output(
        self,
        params: Optional[AgentOutputParams] = None,
        **kwargs,
    ) -> None:

        if params is None and not kwargs:
            raise ValueError("Either params or keyword arguments must be provided.")

        if params is None:
            params = AgentOutputParams(**kwargs)

        query = """
        INSERT INTO agent_outputs (
            agent_name,
            session_id,
            process_id,
            output_json,
            summary,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(agent_name, session_id, process_id)
        DO UPDATE SET
            output_json = excluded.output_json,
            summary = excluded.summary,
            updated_at = CURRENT_TIMESTAMP
        """

        payload_json = params.output.model_dump_json()

        async with self.get_connection() as conn:
            await conn.execute(
                query,
                (
                    params.agent_name,
                    params.session_id,
                    params.process_id,
                    payload_json,
                    params.summary,
                ),
            )
            await conn.commit()

    # =========================
    # GET AGENT OUTPUT
    # =========================

    async def get_agent_output(
        self,
        agent_name: str,
        process_id: str,
        output_model=None,
        session_id: Optional[str] = None,
    ):
        conditions = ["agent_name = ?", "process_id = ?"]
        args: List[Any] = [agent_name, process_id]

        if session_id is not None:
            conditions.append("session_id = ?")
            args.append(session_id)

        query = f"""
        SELECT output_json
        FROM agent_outputs
        WHERE {" AND ".join(conditions)}
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, tuple(args))
            row = await cursor.fetchone()

            if not row:
                return None

            output_json = row["output_json"]

            if output_model:
                return output_model.model_validate_json(output_json)

            return json.loads(output_json)

    # =========================
    # GET FAILURE
    # =========================

    async def get_agent_failure(self, process_id: str) -> Optional[Dict[str, Any]]:
        query = """
        SELECT
            id,
            agent_name,
            session_id,
            process_id,
            reason,
            recommendation,
            created_at
        FROM agent_failures
        WHERE process_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, (process_id,))
            row = await cursor.fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "agent_name": row["agent_name"],
                "session_id": row["session_id"],
                "process_id": row["process_id"],
                "reason": row["reason"],
                "recommendation": row["recommendation"],
                "created_at": row["created_at"],
            }

    # =========================
    # SAVE FAILURE
    # =========================

    async def save_agent_failure(
        self,
        params: Optional[AgentFailureParams] = None,
        **kwargs,
    ) -> None:

        if params is None and not kwargs:
            raise ValueError("Either params or keyword arguments must be provided.")

        if params is None:
            params = AgentFailureParams(**kwargs)

        query = """
        INSERT INTO agent_failures (
            agent_name,
            session_id,
            process_id,
            reason,
            recommendation,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(session_id, process_id)
        DO UPDATE SET
            agent_name = excluded.agent_name,
            reason = excluded.reason,
            recommendation = excluded.recommendation,
            created_at = CURRENT_TIMESTAMP
        """

        async with self.get_connection() as conn:
            await conn.execute(
                query,
                (
                    params.agent_name,
                    params.session_id,
                    params.process_id,
                    params.reason,
                    params.recommendation,
                ),
            )
            await conn.commit()

        logger.info(
            "Saved failure for agent '%s' in session %s",
            params.agent_name,
            params.session_id,
        )

        # =========================
        # FINAL REPORT INSERT (optional)
        # =========================

        try:
            party_id = params.party_id

            if not party_id:
                da_output = await self.get_agent_output(
                    agent_name="Data Analyst",
                    session_id=params.session_id,
                    process_id=params.process_id,
                    output_model=None,
                )

                if da_output:
                    party_id = da_output.get("party_info", {}).get("party_id")

            if party_id:
                query = """
                INSERT INTO final_report (
                    party_id,
                    new_review_id,
                    session_id,
                    process_id,
                    overview_summary,
                    next_steps,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """

                async with self.get_connection() as conn:
                    await conn.execute(
                        query,
                        (
                            party_id,
                            "FAILED",
                            params.session_id,
                            params.process_id,
                            params.reason,
                            params.recommendation,
                        ),
                    )
                    await conn.commit()

        except Exception as e:
            logger.error("Error saving failure to final_report: %s", e)

    # =========================
    # AGENT SUMMARIES
    # =========================

    async def get_all_agent_summaries(
        self, session_id: str, process_id: str
    ) -> List[Dict[str, Any]]:

        query = """
        SELECT agent_name, summary, updated_at
        FROM agent_outputs
        WHERE session_id = ? AND process_id = ? AND summary IS NOT NULL
        ORDER BY updated_at ASC
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, (session_id, process_id))
            rows = await cursor.fetchall()

            return [
                {
                    "agent_name": row["agent_name"],
                    "summary_text": row["summary"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]

    # =========================
    # PROMPTS
    # =========================

    async def get_agent_prompt(
        self, prompt_index: float, model_name: str = LLM_MODEL
    ) -> Optional[str]:

        base_index = int(prompt_index)

        query = """
        SELECT prompt_content, prompt_index, agent_name, model_name
        FROM lu_agent_prompts
        WHERE prompt_index >= ?
          AND prompt_index < ?
          AND model_name = ?
        ORDER BY prompt_index DESC
        LIMIT 1
        """

        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(
                    query,
                    (float(base_index), float(base_index + 1), model_name),
                )
                row = await cursor.fetchone()

            if row:
                return row["prompt_content"]

            return None

        except Exception as e:
            logger.error("Error retrieving prompt: %s", e)
            return None

    # =========================
    # MESSAGES
    # =========================

    async def log_agent_message(
        self,
        params: Optional[AgentMessageParams] = None,
        **kwargs,
    ) -> bool:

        if params is None and not kwargs:
            raise ValueError("Either params or keyword arguments must be provided.")

        if params is None:
            params = AgentMessageParams(**kwargs)

        try:
            message_id = str(uuid.uuid4())
            payload_json = json.dumps(params.payload)

            query = """
            INSERT INTO agent_messages (
                id,
                session_id,
                process_id,
                payload,
                project_id,
                user_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """

            async with self.get_connection() as conn:
                await conn.execute(
                    query,
                    (
                        message_id,
                        params.session_id,
                        params.process_id,
                        payload_json,
                        params.project_id,
                        params.user_id,
                    ),
                )
                await conn.commit()

            return True

        except Exception as e:
            logger.error("Failed to insert agent message: %s", e)
            return False

    # =========================
    # GET MESSAGES
    # =========================

    async def get_agent_messages(self, process_id: str) -> List[Dict[str, Any]]:

        query = """
        SELECT payload, created_at
        FROM agent_messages
        WHERE process_id = ?
        ORDER BY created_at ASC
        """

        async with self.get_connection() as conn:
            cursor = await conn.execute(query, (process_id,))
            rows = await cursor.fetchall()

        messages = []
        for row in rows:
            payload = json.loads(row["payload"])
            payload["timestamp"] = row["created_at"]
            messages.append(payload)

        return messages

    # =========================
    # TOKEN USAGE
    # =========================

    async def save_agent_token_usage(
        self,
        params: Optional[AgentTokenUsageParams] = None,
        **kwargs,
    ) -> None:

        if params is None and not kwargs:
            raise ValueError("Either params or keyword arguments must be provided.")

        if params is None:
            params = AgentTokenUsageParams(**kwargs)

        total = (params.input_tokens or 0) + (params.output_tokens or 0)

        query = """
        INSERT INTO agent_token_usage
            (process_id, agent_name, input_tokens, output_tokens, total_tokens, response_preview)
        VALUES (?, ?, ?, ?, ?, ?)
        """

        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    query,
                    (
                        params.process_id,
                        params.agent_name,
                        params.input_tokens,
                        params.output_tokens,
                        total,
                        params.response_preview,
                    ),
                )
                await conn.commit()

        except Exception as e:
            logger.error("Error saving token usage: %s", e)
