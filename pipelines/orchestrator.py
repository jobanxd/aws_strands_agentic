"""
pipelines/orchestrator.py
──────────────────────────
Top-level orchestrator. Creates PipelineState, runs DRM then ODD.
"""

import logging
from pipelines.data_request_manager import DataRequestManager
from pipelines.odd_validator import ODDValidator
from utils.state import PipelineState
from utils.exceptions import InsufficientDataError, ValidationError, PipelineError
from database.sqlite_manager import SQLiteDatabaseManager

logger = logging.getLogger(__name__)


class Orchestrator:

    def __init__(self):
        self.drm = DataRequestManager()
        self.odd = ODDValidator()

    def process(self, query: str) -> dict:
        # Create state once — shared across the entire pipeline
        state = PipelineState(
            query=query,
            db=SQLiteDatabaseManager(),
        )

        logger.info("Orchestrator | received query: %s", query[:80])

        try:
            state = self.drm.run(state)
        except InsufficientDataError as exc:
            logger.warning("Orchestrator | early exit: %s", exc)
            return {
                "status": "insufficient_data",
                "output": str(exc),
                "stopped_at": state.stopped_at or "DataAnalystAgent",
                "steps_completed": state.steps_completed,
            }
        except PipelineError as exc:
            logger.error("Orchestrator | DRM error: %s", exc)
            return {
                "status": "error",
                "output": str(exc),
                "stopped_at": "DataRequestManager",
                "steps_completed": state.steps_completed,
            }

        try:
            state = self.odd.run(state)
        except ValidationError as exc:
            logger.error("Orchestrator | validation failed: %s", exc)
            return {
                "status": "validation_failed",
                "output": str(exc),
                "stopped_at": "VerifierAgent",
                "steps_completed": state.steps_completed,
            }
        except PipelineError as exc:
            logger.error("Orchestrator | ODD error: %s", exc)
            return {
                "status": "error",
                "output": str(exc),
                "stopped_at": "ODDValidator",
                "steps_completed": state.steps_completed,
            }

        state.status = "success"
        logger.info("Orchestrator | pipeline completed successfully")
        return {
            "status": "success",
            "output": state.data_analyst_output.summary if state.data_analyst_output else "Done",
            "stopped_at": None,
            "steps_completed": state.steps_completed,
        }
