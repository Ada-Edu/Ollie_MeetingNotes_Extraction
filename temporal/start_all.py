"""
Start both the Temporal worker and the API server.

This allows the system to process workflows and accept trigger requests.
"""

import asyncio
import logging
import sys
import os
from concurrent.futures import ThreadPoolExecutor

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_worker():
    """Run the Temporal worker."""
    logger.info("Starting Temporal worker...")

    # Import and run the worker
    import subprocess
    import sys

    # Run worker as separate process
    worker_process = subprocess.Popen(
        [sys.executable, "src/worker.py"],
        cwd=os.path.dirname(__file__)
    )

    # Wait for the process (it will run indefinitely)
    try:
        await asyncio.get_event_loop().run_in_executor(None, worker_process.wait)
    except asyncio.CancelledError:
        worker_process.terminate()
        raise


async def run_api():
    """Run the API server."""
    logger.info("Starting API server...")

    from api.workflow_trigger import app
    import uvicorn

    port = int(os.getenv("API_PORT", "8000"))

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Start both worker and API concurrently."""
    logger.info("=" * 60)
    logger.info("Starting Meeting Notes Extraction System")
    logger.info("=" * 60)
    logger.info("Components:")
    logger.info("  - Temporal Worker (processes workflows)")
    logger.info("  - API Server (receives trigger requests)")
    logger.info("=" * 60)

    # Run both concurrently
    await asyncio.gather(
        run_worker(),
        run_api(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
