"""
Tests for task manager and cancellation functionality.
"""

import asyncio

import pytest

from src.services.task_manager import TaskManager, get_task_manager


class TestTaskManager:
    """Tests for TaskManager singleton."""

    def test_singleton_instance(self) -> None:
        """Test that TaskManager is a singleton."""
        manager1 = get_task_manager()
        manager2 = get_task_manager()
        manager3 = TaskManager()

        assert manager1 is manager2
        assert manager1 is manager3

    @pytest.mark.asyncio
    async def test_register_and_cancel_task(self) -> None:
        """Test registering and cancelling a task."""
        manager = get_task_manager()
        session_id = "test-session-123"

        # Create a long-running task
        async def long_task():
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                return "cancelled"
            return "completed"

        task = asyncio.create_task(long_task())
        manager.register_task(session_id, task)

        # Verify task is active
        assert manager.is_active(session_id)

        # Cancel the task
        result = manager.cancel_task(session_id)
        assert result is True

        # Wait for task to complete
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify task is no longer active
        assert not manager.is_active(session_id)

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self) -> None:
        """Test cancelling a task that doesn't exist."""
        manager = get_task_manager()
        result = manager.cancel_task("nonexistent-session")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_completed_task(self) -> None:
        """Test cancelling a task that already completed."""
        manager = get_task_manager()
        session_id = "completed-session"

        # Create a quick task
        async def quick_task():
            return "done"

        task = asyncio.create_task(quick_task())
        manager.register_task(session_id, task)

        # Wait for completion
        await task

        # Try to cancel already-completed task
        result = manager.cancel_task(session_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_auto_cleanup_on_completion(self) -> None:
        """Test that tasks are auto-cleaned up when they complete."""
        manager = get_task_manager()
        session_id = "auto-cleanup-session"

        initial_count = manager.get_active_count()

        # Create and register a quick task
        async def quick_task():
            await asyncio.sleep(0.1)
            return "done"

        task = asyncio.create_task(quick_task())
        manager.register_task(session_id, task)

        assert manager.get_active_count() == initial_count + 1

        # Wait for completion
        await task
        await asyncio.sleep(0.1)  # Give time for cleanup callback

        # Task should be auto-removed
        assert manager.get_active_count() == initial_count

    @pytest.mark.asyncio
    async def test_multiple_concurrent_tasks(self) -> None:
        """Test managing multiple concurrent tasks."""
        manager = get_task_manager()

        sessions = [f"session-{i}" for i in range(5)]

        async def worker(delay: float):
            await asyncio.sleep(delay)
            return "done"

        # Register multiple tasks
        tasks = []
        for i, session_id in enumerate(sessions):
            task = asyncio.create_task(worker(0.1 * (i + 1)))
            manager.register_task(session_id, task)
            tasks.append(task)

        # All should be active
        for session_id in sessions:
            assert manager.is_active(session_id)

        # Cancel middle task
        middle_session = sessions[2]
        manager.cancel_task(middle_session)

        # Wait for all
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Middle task should be cancelled
        assert isinstance(results[2], asyncio.CancelledError)

        # Others should complete normally
        assert results[0] == "done"
        assert results[1] == "done"
        assert results[3] == "done"
        assert results[4] == "done"
