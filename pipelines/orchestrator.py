"""
pipelines/orchestrator.py
──────────────────────────
Top-level orchestrator. Entry point for every query.

Responsibilities:
  1. Receive the query
  2. Run DataRequestManager
  3. On success, run ODDValidator
  4. On InsufficientDataError, stop and return early-exit response
  5. On any other error, log and raise

This is the ONLY file the application entry point (main.py) should import.
"""

from pipelines.data_request_manager import DataRequestManager
from pipelines.odd_validator import ODDValidator
from utils.exceptions import InsufficientDataError, ValidationError, PipelineError
from utils.logger import logger


class Orchestrator:
    """
    Top-level orchestrator agent.
    Coordinates DataRequestManager and ODDValidator.
    """

    def __init__(self):
        self.drm = DataRequestManager()
        self.odd = ODDValidator()

    def process(self, query: str) -> dict:
        """
        Processes a query through the full pipeline.

        Returns a result dict:
          {
            "status":  "success" | "insufficient_data" | "validation_failed" | "error",
            "output":  <str>,
            "stopped_at": <str | None>   # which agent halted the pipeline
          }
        """
        logger.info(f"Orchestrator | received query: {query[:80]}...")

        # ── Stage 1: Data Request Manager ─────────────────────────────────
        try:
            drm_output = self.drm.run(query)

        except InsufficientDataError as exc:
            # Expected edge case — data analyst flagged insufficient data
            logger.warning(f"Orchestrator | early exit at DataAnalystAgent: {exc}")
            return {
                "status": "insufficient_data",
                "output": str(exc),
                "stopped_at": "DataAnalystAgent",
            }

        except PipelineError as exc:
            logger.error(f"Orchestrator | DRM pipeline error: {exc}")
            return {
                "status": "error",
                "output": str(exc),
                "stopped_at": "DataRequestManager",
            }

        # ── Stage 2: ODD Validator ────────────────────────────────────────
        try:
            odd_output = self.odd.run(drm_output)

        except ValidationError as exc:
            logger.error(f"Orchestrator | validation failed: {exc}")
            return {
                "status": "validation_failed",
                "output": str(exc),
                "stopped_at": "VerifierAgent",
            }

        except PipelineError as exc:
            logger.error(f"Orchestrator | ODD pipeline error: {exc}")
            return {
                "status": "error",
                "output": str(exc),
                "stopped_at": "ODDValidator",
            }

        # ── Done ──────────────────────────────────────────────────────────
        logger.info("Orchestrator | pipeline completed successfully")
        return {
            "status": "success",
            "output": odd_output,
            "stopped_at": None,
        }
