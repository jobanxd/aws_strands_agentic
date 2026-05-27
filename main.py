"""
main.py
────────
Application entry point. Run this file to start the agent system.

Usage:
  python main.py
  python main.py "custom query here"
"""

import sys
import json

# Add src/ to path so all imports resolve cleanly
sys.path.insert(0, "src")

from pipelines.orchestrator import Orchestrator
from utils.logger import logger


def main():
    query = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Analyse data request for entity ID 12345 and validate compliance."
    )

    logger.info("=" * 60)
    logger.info("Starting agent pipeline")
    logger.info("=" * 60)

    orchestrator = Orchestrator()
    result = orchestrator.process(query)

    print("\n" + "=" * 60)
    print("PIPELINE RESULT")
    print("=" * 60)
    print(json.dumps(result, indent=2))

    # Exit with non-zero code if pipeline did not succeed
    if result["status"] != "success":
        sys.exit(1)


if __name__ == "__main__":
    main()
