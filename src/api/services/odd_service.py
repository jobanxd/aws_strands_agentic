# src/api/services/odd_service.py

import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from src.workflows.pipelines.orchestrator import Orchestrator
from src.utils.logger import get_logger

logger = get_logger(__name__)

# One shared thread pool — each request gets its own thread
# Adjust max_workers based on your server resources
_executor = ThreadPoolExecutor(max_workers=5)

# In-memory store for process results
# Replace with Redis or DB if you need persistence across restarts
_process_store: dict = {}


class ODDService:

    async def trigger(self, query: str) -> str:
        """
        Accepts a query, assigns a process_id, kicks off the pipeline
        in a background thread, and returns the process_id immediately.
        """
        process_id = str(uuid.uuid4())

        _process_store[process_id] = {
            "process_id": process_id,
            "status": "running",
            "stopped_at": None,
            "steps_completed": [],
            "output": None,
            "error": None,
        }

        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            _executor,
            self._run_pipeline,
            process_id,
            query,
        )

        logger.info(f"ODD process started — process_id: {process_id} | query: {query}")
        return process_id

    def _run_pipeline(self, process_id: str, query: str):
        """
        Runs in a thread from the pool.
        Each call gets a fresh Orchestrator → fresh PipelineState → isolated state.
        """
        try:
            logger.info(f"[{process_id}] Pipeline thread started")
            orchestrator = Orchestrator()       # fresh per request — no shared state
            result = orchestrator.process(query)

            _process_store[process_id].update({
                "status": result.get("status"),
                "stopped_at": result.get("stopped_at"),
                "steps_completed": result.get("steps_completed", []),
                "output": result.get("output"),
                "error": result.get("output") if result.get("status") != "success" else None,
            })
            logger.info(f"[{process_id}] Pipeline complete — status: {result.get('status')}")

        except Exception as exc:
            logger.error(f"[{process_id}] Pipeline crashed: {exc}")
            _process_store[process_id].update({
                "status": "failed",
                "error": str(exc),
            })

    async def get_status(self, process_id: str) -> Optional[dict]:
        """
        Returns the current state of a process by process_id.
        Returns None if process_id is not found.
        """
        return _process_store.get(process_id)