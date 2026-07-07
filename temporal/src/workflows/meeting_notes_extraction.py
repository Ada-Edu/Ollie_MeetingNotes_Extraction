"""Temporal workflow for meeting notes action item extraction."""

from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.meeting_notes import (
        validate_meeting_notes_input,
        call_model_for_action_item_extraction,
        persist_extraction_results,
        record_extraction_failure
    )


@workflow.defn
class ExtractMeetingActionItemsWorkflow:
    """Workflow to extract action items from meeting notes using AI."""

    @workflow.run
    async def run(self, meeting_notes_id: str, notes: str) -> dict:
        """Execute extraction workflow.

        Args:
            meeting_notes_id: ID of meeting_notes record in database
            notes: Raw meeting notes text

        Returns:
            Dict with status, extraction_run_id, and optional error
        """
        workflow_id = workflow.info().workflow_id
        model_info = {}

        workflow.logger.info(
            f"Starting extraction workflow for meeting_notes_id: {meeting_notes_id}"
        )

        try:
            # Step 1: Validate input (fail fast)
            await workflow.execute_activity(
                validate_meeting_notes_input,
                args=[notes],
                start_to_close_timeout=timedelta(seconds=5)
            )

            workflow.logger.info("Input validation passed")

            # Step 2: Call model with retries
            extraction_result = await workflow.execute_activity(
                call_model_for_action_item_extraction,
                args=[notes],
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                    backoff_coefficient=2.0,
                    maximum_attempts=3
                ),
                start_to_close_timeout=timedelta(seconds=30)
            )

            action_items = extraction_result["action_items"]
            model_info = {
                "provider": extraction_result["model_provider"],
                "model_name": extraction_result["model_name"]
            }

            workflow.logger.info(
                f"Model extraction complete: {len(action_items)} items found"
            )

            # Step 3: Persist results to database
            extraction_run_id = await workflow.execute_activity(
                persist_extraction_results,
                args=[
                    meeting_notes_id,
                    workflow_id,
                    action_items,
                    model_info,
                    extraction_result  # Raw response for debugging
                ],
                start_to_close_timeout=timedelta(seconds=10)
            )

            workflow.logger.info(f"Results persisted: extraction_run_id={extraction_run_id}")

            return {
                "status": "completed",
                "extraction_run_id": extraction_run_id,
                "action_items_count": len(action_items),
                "model_provider": model_info["provider"],
                "model_name": model_info["model_name"]
            }

        except Exception as e:
            # Handle any failure
            error_message = str(e)
            workflow.logger.error(f"Extraction workflow failed: {error_message}")

            # Record failure in database
            extraction_run_id = await workflow.execute_activity(
                record_extraction_failure,
                args=[meeting_notes_id, workflow_id, error_message, model_info],
                start_to_close_timeout=timedelta(seconds=10)
            )

            workflow.logger.info(
                f"Failure recorded: extraction_run_id={extraction_run_id}"
            )

            return {
                "status": "failed",
                "extraction_run_id": extraction_run_id,
                "error": error_message,
                "model_provider": model_info.get("provider"),
                "model_name": model_info.get("model_name")
            }
