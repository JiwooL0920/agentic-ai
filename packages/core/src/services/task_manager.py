"""
Task manager for tracking and cancelling active streaming requests.

This singleton service tracks active asyncio tasks to enable cancellation
of long-running agent executions.
"""

import asyncio
from typing import Any

import structlog

logger = structlog.get_logger()


class TaskManager:
    """
    Singleton manager for active streaming tasks.

    Responsibilities:
    - Register active tasks by session_id
    - Cancel tasks on demand
    - Clean up completed tasks
    """

    _instance: "TaskManager | None" = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls) -> "TaskManager":
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tasks: dict[str, asyncio.Task[Any]] = {}
            cls._instance._logger = logger.bind(component="TaskManager")
        return cls._instance

    def register_task(self, session_id: str, task: asyncio.Task[Any]) -> None:
        """
        Register an active task for a session.

        Args:
            session_id: Session identifier
            task: The asyncio task to track
        """
        self._tasks[session_id] = task
        self._logger.info("task_registered", session_id=session_id)

        # Auto-cleanup on task completion
        task.add_done_callback(lambda _: self._cleanup_task(session_id))

    def cancel_task(self, session_id: str) -> bool:
        """
        Cancel an active task for a session.

        Args:
            session_id: Session identifier

        Returns:
            True if task was found and cancelled, False otherwise
        """
        task = self._tasks.get(session_id)
        if not task:
            self._logger.warning("task_not_found", session_id=session_id)
            return False

        if task.done():
            self._logger.info("task_already_done", session_id=session_id)
            self._cleanup_task(session_id)
            return False

        task.cancel()
        self._logger.info("task_cancelled", session_id=session_id)
        return True

    def _cleanup_task(self, session_id: str) -> None:
        """Remove task from registry."""
        if session_id in self._tasks:
            del self._tasks[session_id]
            self._logger.debug("task_cleaned_up", session_id=session_id)

    def get_active_count(self) -> int:
        """Get count of active tasks."""
        return len(self._tasks)

    def is_active(self, session_id: str) -> bool:
        """Check if a task is active for a session."""
        task = self._tasks.get(session_id)
        return task is not None and not task.done()


def get_task_manager() -> TaskManager:
    """Get the singleton TaskManager instance."""
    return TaskManager()
