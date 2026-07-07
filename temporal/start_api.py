"""
Start the Workflow Trigger API server.

This script starts both the Temporal worker and the HTTP API server
that allows the Supabase Edge Function to trigger workflows.
"""

import asyncio
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Start the API server."""
    logger.info("Starting Workflow Trigger API...")

    # Import here to ensure path is set
    from api.workflow_trigger import app
    import uvicorn

    port = int(os.getenv("API_PORT", "8000"))

    # Run the API server
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
