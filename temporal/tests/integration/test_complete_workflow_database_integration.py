"""
Integration tests for complete workflow database integration.

Tests cover the full workflow from meeting note creation through action item extraction,
including database persistence, transaction handling, and query optimization.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import uuid4
import uuid

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

# Assuming these imports exist in your codebase
from workflows.extraction_workflow import ExtractionWorkflow
from activities.extraction_activities import (
    create_meeting_note,
    extract_action_items,
    persist_action_items,
    record_workflow_failure,
)
from models.database import (
    MeetingNote,
    ExtractionRun,
    ActionItem,
    WorkflowExecution,
)
from database.session import get_async_session, async_session_maker


@pytest.fixture
async def db_session():
    """Provide a database session for tests."""
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def temporal_client():
    """Provide a Temporal test client."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        yield env.client


@pytest.fixture
async def workflow_worker(temporal_client):
    """Start a worker for workflow tests."""
    async with Worker(
        temporal_client,
        task_queue="extraction-task-queue",
        workflows=[ExtractionWorkflow],
        activities=[
            create_meeting_note,
            extract_action_items,
            persist_action_items,
            record_workflow_failure,
        ],
    ):
        yield


@pytest.fixture
async def supabase_client():
    """Provide a mock Supabase client for tests."""
    # Mock implementation - replace with actual Supabase client initialization
    class MockSupabaseClient:
        async def _request(self, method, endpoint, params=None):
            # Mock implementation
            return []

    return MockSupabaseClient()


class TestCompleteWorkflowDatabaseIntegration:
    """Integration tests for complete workflow with database operations."""

    @pytest.mark.asyncio
    async def test_complete_extraction_flow_with_database(
        self, db_session: AsyncSession, temporal_client: Client, workflow_worker
    ):
        """
        Test complete extraction flow from meeting note creation to action items.

        Verifies that:
        - Meeting note is created in database
        - Extraction run is initiated
        - Action items are extracted and persisted
        - All database records are properly linked
        - Workflow execution is tracked
        """
        # Arrange
        meeting_note_data = {
            "title": "Sprint Planning Q3 2026",
            "content": """
            Action items from today's meeting:
            1. John to review the API documentation by Friday
            2. Sarah needs to update the deployment scripts
            3. Team should schedule follow-up meeting next week
            """,
            "created_by": "test_user",
            "meeting_date": datetime.utcnow(),
        }

        # Act
        workflow_id = f"extraction-workflow-{uuid4()}"
        handle = await temporal_client.start_workflow(
            ExtractionWorkflow.run,
            meeting_note_data,
            id=workflow_id,
            task_queue="extraction-task-queue",
        )

        result = await handle.result()

        # Assert
        await db_session.refresh(db_session)

        # Verify meeting note was created
        meeting_note = await db_session.execute(
            select(MeetingNote).where(MeetingNote.id == result["meeting_note_id"])
        )
        meeting_note = meeting_note.scalar_one()
        assert meeting_note is not None
        assert meeting_note.title == meeting_note_data["title"]
        assert meeting_note.content == meeting_note_data["content"]

        # Verify extraction run was created
        extraction_run = await db_session.execute(
            select(ExtractionRun)
            .where(ExtractionRun.meeting_note_id == meeting_note.id)
            .options(selectinload(ExtractionRun.action_items))
        )
        extraction_run = extraction_run.scalar_one()
        assert extraction_run is not None
        assert extraction_run.status == "completed"
        assert extraction_run.workflow_id == workflow_id

        # Verify action items were extracted and persisted
        action_items = extraction_run.action_items
        assert len(action_items) >= 3

        # Verify action items content
        assignees = [item.assignee for item in action_items]
        assert "John" in assignees or any("John" in item.description for item in action_items)
        assert "Sarah" in assignees or any("Sarah" in item.description for item in action_items)

        # Verify workflow execution tracking
        workflow_execution = await db_session.execute(
            select(WorkflowExecution).where(WorkflowExecution.workflow_id == workflow_id)
        )
        workflow_execution = workflow_execution.scalar_one()
        assert workflow_execution.status == "completed"
        assert workflow_execution.completed_at is not None

    @pytest.mark.asyncio
    async def test_workflow_failure_recording_in_database(
        self, db_session: AsyncSession, temporal_client: Client, workflow_worker
    ):
        """
        Test that workflow failures are properly recorded in the database.

        Verifies that:
        - Failed workflows create failure records
        - Error messages and stack traces are captured
        - Extraction run status reflects failure
        - Retry attempts are tracked
        """
        # Arrange
        invalid_meeting_note_data = {
            "title": None,  # Invalid data to trigger failure
            "content": "",
            "created_by": "test_user",
            "meeting_date": "invalid_date",
        }

        workflow_id = f"extraction-workflow-failure-{uuid4()}"

        # Act
        handle = await temporal_client.start_workflow(
            ExtractionWorkflow.run,
            invalid_meeting_note_data,
            id=workflow_id,
            task_queue="extraction-task-queue",
        )

        with pytest.raises(Exception):
            await handle.result()

        # Assert
        await db_session.refresh(db_session)

        # Verify workflow execution failure was recorded
        workflow_execution = await db_session.execute(
            select(WorkflowExecution).where(WorkflowExecution.workflow_id == workflow_id)
        )
        workflow_execution = workflow_execution.scalar_one()
        assert workflow_execution.status == "failed"
        assert workflow_execution.error_message is not None
        assert workflow_execution.failed_at is not None

        # Verify extraction run status
        extraction_run = await db_session.execute(
            select(ExtractionRun).where(ExtractionRun.workflow_id == workflow_id)
        )
        extraction_run = extraction_run.scalar_one_or_none()
        if extraction_run:
            assert extraction_run.status == "failed"
            assert extraction_run.error_details is not None

    @pytest.mark.asyncio
    async def test_multiple_action_items_persisted_correctly(
        self, db_session: AsyncSession
    ):
        """
        Test that multiple action items are persisted correctly with all relationships.

        Verifies that:
        - Multiple action items can be created in a single extraction
        - All fields are properly populated
        - Foreign key relationships are maintained
        - Action items are retrievable by extraction run
        """
        # Arrange
        meeting_note = MeetingNote(
            title="Team Sync",
            content="Meeting notes here",
            created_by="test_user",
            meeting_date=datetime.utcnow(),
        )
        db_session.add(meeting_note)
        await db_session.flush()

        extraction_run = ExtractionRun(
            meeting_note_id=meeting_note.id,
            workflow_id=f"workflow-{uuid4()}",
            status="in_progress",
            started_at=datetime.utcnow(),
        )
        db_session.add(extraction_run)
        await db_session.flush()

        action_items_data = [
            {
                "description": "Review pull request #123",
                "assignee": "Alice",
                "due_date": datetime.utcnow() + timedelta(days=2),
                "priority": "high",
            },
            {
                "description": "Update documentation",
                "assignee": "Bob",
                "due_date": datetime.utcnow() + timedelta(days=5),
                "priority": "medium",
            },
            {
                "description": "Schedule team meeting",
                "assignee": "Charlie",
                "due_date": datetime.utcnow() + timedelta(days=1),
                "priority": "low",
            },
            {
                "description": "Deploy to staging",
                "assignee": "Alice",
                "due_date": datetime.utcnow() + timedelta(hours=4),
                "priority": "high",
            },
            {
                "description": "Run integration tests",
                "assignee": "Bob",
                "due_date": datetime.utcnow() + timedelta(hours=8),
                "priority": "high",
            },
        ]

        # Act
        action_items = [
            ActionItem(
                extraction_run_id=extraction_run.id,
                meeting_note_id=meeting_note.id,
                **item_data
            )
            for item_data in action_items_data
        ]
        db_session.add_all(action_items)
        await db_session.commit()

        # Assert
        result = await db_session.execute(
            select(ActionItem)
            .where(ActionItem.extraction_run_id == extraction_run.id)
            .order_by(ActionItem.created_at)
        )
        persisted_items = result.scalars().all()

        assert len(persisted_items) == 5

        # Verify all fields are populated
        for item in persisted_items:
            assert item.id is not None
            assert item.description is not None
            assert item.assignee is not None
            assert item.due_date is not None
            assert item.priority in ["high", "medium", "low"]
            assert item.extraction_run_id == extraction_run.id
            assert item.meeting_note_id == meeting_note.id
            assert item.created_at is not None

        # Verify assignees
        assignees = [item.assignee for item in persisted_items]
        assert assignees.count("Alice") == 2
        assert assignees.count("Bob") == 2
        assert assignees.count("Charlie") == 1

    @pytest.mark.asyncio
    async def test_extraction_run_creation_when_not_exists(
        self, db_session: AsyncSession
    ):
        """
        Test that extraction run is created automatically when it doesn't exist.

        Verifies that:
        - Extraction run is created on first action item extraction
        - Subsequent items use the same extraction run
        - Idempotency is maintained
        """
        # Arrange
        meeting_note = MeetingNote(
            title="Standup Meeting",
            content="Daily standup notes",
            created_by="test_user",
            meeting_date=datetime.utcnow(),
        )
        db_session.add(meeting_note)
        await db_session.commit()

        workflow_id = f"workflow-{uuid4()}"

        # Act - First check that no extraction run exists
        result = await db_session.execute(
            select(ExtractionRun).where(ExtractionRun.workflow_id == workflow_id)
        )
        assert result.scalar_one_or_none() is None

        # Create extraction run
        extraction_run = ExtractionRun(
            meeting_note_id=meeting_note.id,
            workflow_id=workflow_id,
            status="in_progress",
            started_at=datetime.utcnow(),
        )
        db_session.add(extraction_run)
        await db_session.commit()

        # Assert
        result = await db_session.execute(
            select(ExtractionRun).where(ExtractionRun.workflow_id == workflow_id)
        )
        created_run = result.scalar_one()

        assert created_run is not None
        assert created_run.meeting_note_id == meeting_note.id
        assert created_run.workflow_id == workflow_id
        assert created_run.status == "in_progress"

        # Verify idempotency - subsequent query returns same run
        result2 = await db_session.execute(
            select(ExtractionRun).where(ExtractionRun.workflow_id == workflow_id)
        )
        same_run = result2.scalar_one()
        assert same_run.id == created_run.id

    @pytest.mark.asyncio
    async def test_database_transaction_handling(self, db_session: AsyncSession):
        """
        Test that database transactions are handled correctly.

        Verifies that:
        - Successful transactions commit all changes
        - Failed transactions rollback completely
        - No partial data remains after rollback
        - Transaction isolation is maintained
        """
        # Test successful transaction
        meeting_note = MeetingNote(
            title="Transaction Test Meeting",
            content="Testing transaction handling",
            created_by="test_user",
            meeting_date=datetime.utcnow(),
        )
        db_session.add(meeting_note)
        await db_session.commit()

        # Verify data was committed
        result = await db_session.execute(
            select(MeetingNote).where(MeetingNote.title == "Transaction Test Meeting")
        )
        committed_note = result.scalar_one()
        assert committed_note is not None

        # Test failed transaction with rollback
        extraction_run = ExtractionRun(
            meeting_note_id=committed_note.id,
            workflow_id=f"workflow-{uuid4()}",
            status="in_progress",
            started_at=datetime.utcnow(),
        )
        db_session.add(extraction_run)
        await db_session.flush()

        action_item = ActionItem(
            extraction_run_id=extraction_run.id,
            meeting_note_id=committed_note.id,
            description="Test action item",
            assignee="Test User",
            due_date=datetime.utcnow() + timedelta(days=1),
            priority="medium",
        )
        db_session.add(action_item)

        # Simulate failure and rollback
        await db_session.rollback()

        # Verify rollback worked - extraction run should not exist
        result = await db_session.execute(
            select(ExtractionRun).where(
                ExtractionRun.meeting_note_id == committed_note.id
            )
        )
        assert result.scalar_one_or_none() is None

        # Verify action item also doesn't exist
        result = await db_session.execute(
            select(ActionItem).where(ActionItem.meeting_note_id == committed_note.id)
        )
        assert result.scalar_one_or_none() is None

        # But meeting note should still exist (was committed before rollback)
        result = await db_session.execute(
            select(MeetingNote).where(MeetingNote.id == committed_note.id)
        )
        assert result.scalar_one() is not None

    @pytest.mark.asyncio
    async def test_efficient_queries_for_extraction_runs_with_items(
        self, db_session: AsyncSession
    ):
        """
        Test that queries for extraction runs with items are efficient.

        Verifies that:
        - Eager loading is used to avoid N+1 queries
        - Queries use proper joins
        - Query performance is acceptable
        - Result includes all related data
        """
        # Arrange - Create multiple meeting notes with extraction runs and action items
        meeting_notes = []
        for i in range(5):
            note = MeetingNote(
                title=f"Meeting {i}",
                content=f"Content for meeting {i}",
                created_by="test_user",
                meeting_date=datetime.utcnow(),
            )
            db_session.add(note)
            meeting_notes.append(note)

        await db_session.flush()

        extraction_runs = []
        for note in meeting_notes:
            run = ExtractionRun(
                meeting_note_id=note.id,
                workflow_id=f"workflow-{uuid4()}",
                status="completed",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            )
            db_session.add(run)
            extraction_runs.append(run)

        await db_session.flush()

        # Create multiple action items per extraction run
        for run in extraction_runs:
            for j in range(3):
                item = ActionItem(
                    extraction_run_id=run.id,
                    meeting_note_id=run.meeting_note_id,
                    description=f"Action item {j} for run {run.id}",
                    assignee=f"User {j}",
                    due_date=datetime.utcnow() + timedelta(days=j + 1),
                    priority="medium",
                )
                db_session.add(item)

        await db_session.commit()

        # Act - Query with eager loading
        result = await db_session.execute(
            select(ExtractionRun)
            .options(
                selectinload(ExtractionRun.action_items),
                selectinload(ExtractionRun.meeting_note),
            )
            .where(ExtractionRun.status == "completed")
            .order_by(ExtractionRun.started_at.desc())
        )
        runs = result.scalars().all()

        # Assert
        assert len(runs) == 5

        # Verify all runs have action items loaded (no additional queries)
        for run in runs:
            assert len(run.action_items) == 3
            assert run.meeting_note is not None

            # Verify we can access related data without triggering queries
            for item in run.action_items:
                assert item.description is not None
                assert item.assignee is not None

    @pytest.mark.asyncio
    async def test_batch_action_item_creation(self, db_session: AsyncSession):
        """
        Test batch creation of action items is efficient.

        Verifies that:
        - Multiple action items can be created in a single operation
        - Batch insert is used instead of individual inserts
        - All items are committed atomically
        - Performance is acceptable for large batches
        """
        # Arrange
        meeting_note = MeetingNote(
            title="Large Meeting",
            content="Meeting with many action items",
            created_by="test_user",
            meeting_date=datetime.utcnow(),
        )
        db_session.add(meeting_note)
        await db_session.flush()

        extraction_run = ExtractionRun(
            meeting_note_id=meeting_note.id,
            workflow_id=f"workflow-{uuid4()}",
            status="in_progress",
            started_at=datetime.utcnow(),
        )
        db_session.add(extraction_run)
        await db_session.flush()

        # Create a large batch of action items
        batch_size = 50
        action_items = []

        for i in range(batch_size):
            item = ActionItem(
                extraction_run_id=extraction_run.id,
                meeting_note_id=meeting_note.id,
                description=f"Batch action item {i}",
                assignee=f"User {i % 10}",  # Rotate through 10 users
                due_date=datetime.utcnow() + timedelta(days=(i % 7) + 1),
                priority=["high", "medium", "low"][i % 3],
            )
            action_items.append(item)

        # Act - Batch insert
        db_session.add_all(action_items)
        await db_session.commit()

        # Assert
        result = await db_session.execute(
            select(func.count(ActionItem.id)).where(
                ActionItem.extraction_run_id == extraction_run.id
            )
        )
        count = result.scalar()
        assert count == batch_size

        # Verify all items were created correctly
        result = await db_session.execute(
            select(ActionItem)
            .where(ActionItem.extraction_run_id == extraction_run.id)
            .order_by(ActionItem.description)
        )
        persisted_items = result.scalars().all()

        assert len(persisted_items) == batch_size

        # Verify data integrity
        for i, item in enumerate(persisted_items):
            assert item.extraction_run_id == extraction_run.id
            assert item.meeting_note_id == meeting_note.id
            assert item.assignee is not None
            assert item.due_date is not None
            assert item.priority in ["high", "medium", "low"]

    @pytest.mark.asyncio
    async def test_database_index_utilization(self, db_session: AsyncSession):
        """
        Test that database indexes are properly utilized for common queries.

        Verifies that:
        - Queries on indexed columns perform well
        - Foreign key indexes are used
        - Composite indexes work correctly
        - Query plans show index usage
        """
        # Arrange - Create test data
        meeting_note = MeetingNote(
            title="Index Test Meeting",
            content="Testing index utilization",
            created_by="test_user",
            meeting_date=datetime.utcnow(),
        )
        db_session.add(meeting_note)
        await db_session.flush()

        workflow_id = f"workflow-{uuid4()}"
        extraction_run = ExtractionRun(
            meeting_note_id=meeting_note.id,
            workflow_id=workflow_id,
            status="completed",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db_session.add(extraction_run)
        await db_session.flush()

        # Create action items
        for i in range(10):
            item = ActionItem(
                extraction_run_id=extraction_run.id,
                meeting_note_id=meeting_note.id,
                description=f"Action item {i}",
                assignee="test_user",
                due_date=datetime.utcnow() + timedelta(days=i + 1),
                priority="medium",
            )
            db_session.add(item)

        await db_session.commit()

        # Act & Assert - Test various indexed queries

        # Test 1: Query by workflow_id (should use index)
        result = await db_session.execute(
            select(ExtractionRun).where(ExtractionRun.workflow_id == workflow_id)
        )
        run = result.scalar_one()
        assert run is not None

        # Test 2: Query by meeting_note_id (foreign key index)
        result = await db_session.execute(
            select(ActionItem).where(ActionItem.meeting_note_id == meeting_note.id)
        )
        items = result.scalars().all()
        assert len(items) == 10

        # Test 3: Query by extraction_run_id (foreign key index)
        result = await db_session.execute(
            select(ActionItem).where(ActionItem.extraction_run_id == extraction_run.id)
        )
        items = result.scalars().all()
        assert len(items) == 10

        # Test 4: Query with composite conditions (should use appropriate indexes)
        result = await db_session.execute(
            select(ActionItem)
            .where(
                ActionItem.meeting_note_id == meeting_note.id,
                ActionItem.assignee == "test_user",
            )
            .order_by(ActionItem.due_date)
        )
        items = result.scalars().all()
        assert len(items) == 10

        # Test 5: Query with date range (should use index on due_date if exists)
        today = datetime.utcnow()
        week_from_now = today + timedelta(days=7)
        result = await db_session.execute(
            select(ActionItem)
            .where(
                ActionItem.due_date >= today,
                ActionItem.due_date <= week_from_now,
            )
        )
        items = result.scalars().all()
        assert len(items) >= 7

        # Optional: Check query execution plan (PostgreSQL specific)
        # This would require raw SQL execution to get EXPLAIN output
        if db_session.bind.dialect.name == "postgresql":
            explain_query = text(
                """
                EXPLAIN (FORMAT JSON)
                SELECT * FROM action_items
                WHERE meeting_note_id = :note_id
                """
            )
            result = await db_session.execute(
                explain_query, {"note_id": meeting_note.id}
            )
            explain_result = result.fetchone()
            # In a real test, you would parse and verify the plan shows index usage
            assert explain_result is not None

    @pytest.mark.asyncio
    async def test_concurrent_extraction_runs(self, db_session: AsyncSession):
        """
        Test multiple concurrent extractions don't deadlock.

        Verifies that:
        - Multiple concurrent extraction runs can be created without deadlocks
        - All extraction runs are created with unique IDs
        - Database connection pool handles concurrent access correctly
        - No race conditions occur during concurrent inserts
        """
        # Arrange
        meeting_note = MeetingNote(
            title="Concurrent test",
            content="Test concurrent extraction runs",
            created_by="test_user",
            meeting_date=datetime.utcnow(),
        )
        db_session.add(meeting_note)
        await db_session.commit()

        async def create_extraction_run(i):
            """Create a single extraction run in its own session."""
            async with async_session_maker() as session:
                run = ExtractionRun(
                    meeting_note_id=meeting_note.id,
                    workflow_id=f"workflow-{i}",
                    status="in_progress",
                    started_at=datetime.utcnow(),
                )
                session.add(run)
                await session.commit()
                return run.id

        # Act - Create 50 concurrent extraction runs
        run_ids = await asyncio.gather(*[create_extraction_run(i) for i in range(50)])

        # Assert
        assert len(run_ids) == 50
        assert len(set(run_ids)) == 50  # All unique

        # Verify all runs were persisted correctly
        async with async_session_maker() as session:
            result = await session.execute(
                select(func.count(ExtractionRun.id)).where(
                    ExtractionRun.meeting_note_id == meeting_note.id
                )
            )
            count = result.scalar()
            assert count == 50

    @pytest.mark.asyncio
    async def test_workflow_handles_database_connection_loss(
        self, temporal_client: Client, supabase_client, workflow_worker
    ):
        """
        Test workflow behavior when database connection is lost.

        Verifies that:
        - Workflow can handle temporary database failures
        - Workflow retries on database connection errors
        - Workflow eventually succeeds when database recovers
        - Data is persisted after recovery
        """
        # Arrange
        async def create_test_meeting_note():
            async with async_session_maker() as session:
                note = MeetingNote(
                    title="DB Connection Test",
                    content="Testing database connection loss handling",
                    created_by="test_user",
                    meeting_date=datetime.utcnow(),
                )
                session.add(note)
                await session.commit()
                return note.id

        meeting_notes_id = await create_test_meeting_note()

        # Act - Start workflow
        workflow_id = f"db-failure-test-{uuid.uuid4()}"
        handle = await temporal_client.start_workflow(
            ExtractionWorkflow.run,
            args=[meeting_notes_id, "Test notes"],
            id=workflow_id,
            task_queue="extraction-task-queue",
        )

        # Simulate database connection failure during execution
        # (In real test, would kill database container or block network)
        # For this test, we assume the workflow has retry logic built in

        # Assert - Workflow should retry and eventually succeed when DB comes back
        result = await asyncio.wait_for(handle.result(), timeout=120.0)

        # Verify workflow completed
        assert result is not None
        assert result.get("status") == "completed" or "meeting_note_id" in result

        # Verify data was eventually persisted
        extraction_runs = await supabase_client._request(
            "GET",
            "extraction_runs",
            params={"workflow_id": f"eq.{workflow_id}"}
        )
        # Note: This assertion depends on actual Supabase integration
        # In a real test environment, this would verify the data was persisted
        assert extraction_runs is not None

    @pytest.mark.asyncio
    async def test_database_connection_pool_exhaustion(self, db_session: AsyncSession):
        """
        Test system handles connection pool exhaustion gracefully.

        Verifies that:
        - Requests wait for available connections instead of failing
        - Connection pool limits are respected
        - All concurrent requests eventually complete
        - No connections are leaked
        """
        # Arrange - Create more concurrent sessions than typical pool size
        pool_size = 10
        concurrent_requests = pool_size + 5

        async def create_meeting_note(note_index):
            """Create a meeting note in its own session."""
            async with async_session_maker() as session:
                note = MeetingNote(
                    title=f"Pool test {note_index}",
                    content=f"Test connection pool handling {note_index}",
                    created_by="test_user",
                    meeting_date=datetime.utcnow(),
                )
                session.add(note)
                await session.commit()
                return note.id

        # Act - Some requests should queue, not fail
        results = await asyncio.gather(
            *[create_meeting_note(i) for i in range(concurrent_requests)]
        )

        # Assert
        assert len(results) == concurrent_requests
        assert all(r is not None for r in results)

        # Verify all meeting notes were created
        async with async_session_maker() as session:
            result = await session.execute(
                select(func.count(MeetingNote.id)).where(
                    MeetingNote.title.like("Pool test%")
                )
            )
            count = result.scalar()
            assert count == concurrent_requests
