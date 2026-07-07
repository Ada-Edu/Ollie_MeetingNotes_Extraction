"""
HTTP API endpoint to trigger Temporal workflows.

This provides a simple REST API that the Supabase Edge Function can call
to trigger Temporal workflows without needing a Temporal client in Deno.
"""

import asyncio
import logging
import os
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from temporalio.client import Client

# Use absolute imports to avoid package structure issues
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Temporal Workflow Trigger API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporal client (initialized on startup)
temporal_client: Client = None


class WorkflowTriggerRequest(BaseModel):
    """Request to trigger a workflow."""
    workflow_name: str
    workflow_id: str
    args: Dict[str, Any]
    task_queue: str = "main"


class WorkflowTriggerResponse(BaseModel):
    """Response from triggering a workflow."""
    success: bool
    workflow_id: str
    message: str


@app.on_event("startup")
async def startup_event():
    """Initialize Temporal client on startup."""
    global temporal_client

    temporal_address = os.getenv("TEMPORAL_ADDRESS", "temporal:7233")
    logger.info(f"Connecting to Temporal at {temporal_address}")

    try:
        temporal_client = await Client.connect(temporal_address)
        logger.info("Successfully connected to Temporal")
    except Exception as e:
        logger.error(f"Failed to connect to Temporal: {e}")
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "temporal_connected": temporal_client is not None
    }


@app.post("/trigger-workflow", response_model=WorkflowTriggerResponse)
async def trigger_workflow(request: WorkflowTriggerRequest):
    """
    Trigger a Temporal workflow.

    Args:
        request: Workflow trigger request with name, ID, args, and task queue

    Returns:
        WorkflowTriggerResponse with success status and workflow ID

    Raises:
        HTTPException: If workflow triggering fails
    """
    logger.info(f"Received workflow trigger request: {request.workflow_name} (ID: {request.workflow_id})")

    if temporal_client is None:
        logger.error("Temporal client not initialized")
        raise HTTPException(status_code=503, detail="Temporal client not connected")

    try:
        # Import workflow class dynamically
        from workflows.meeting_notes_extraction import ExtractMeetingActionItemsWorkflow

        # Map workflow name to workflow class
        workflow_map = {
            "ExtractMeetingActionItemsWorkflow": ExtractMeetingActionItemsWorkflow,
        }

        workflow_class = workflow_map.get(request.workflow_name)
        if workflow_class is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown workflow: {request.workflow_name}"
            )

        # Extract arguments
        meeting_notes_id = request.args.get("meeting_notes_id")
        notes_text = request.args.get("notes_text")

        if not meeting_notes_id or not notes_text:
            raise HTTPException(
                status_code=400,
                detail="Missing required arguments: meeting_notes_id, notes_text"
            )

        logger.info(f"Starting workflow {request.workflow_name} with ID {request.workflow_id}")

        # Start the workflow
        handle = await temporal_client.start_workflow(
            workflow_class.run,
            args=[meeting_notes_id, notes_text],
            id=request.workflow_id,
            task_queue=request.task_queue,
        )

        logger.info(f"Workflow started successfully: {handle.id}")

        return WorkflowTriggerResponse(
            success=True,
            workflow_id=handle.id,
            message=f"Workflow {request.workflow_name} triggered successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger workflow: {str(e)}"
        )


@app.get("/workflow/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """
    Get the status of a running workflow.

    Args:
        workflow_id: The workflow ID

    Returns:
        Workflow status information
    """
    if temporal_client is None:
        raise HTTPException(status_code=503, detail="Temporal client not connected")

    try:
        handle = temporal_client.get_workflow_handle(workflow_id)

        # Try to get result (will raise if workflow not complete)
        try:
            result = await asyncio.wait_for(handle.result(), timeout=0.1)
            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": result
            }
        except asyncio.TimeoutError:
            return {
                "workflow_id": workflow_id,
                "status": "running"
            }

    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workflow status: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", "8000"))
    logger.info(f"Starting Workflow Trigger API on port {port}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
