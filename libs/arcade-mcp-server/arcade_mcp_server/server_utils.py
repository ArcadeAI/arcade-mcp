"""Utilities for server management."""

import os
from types import FrameType

import uvicorn
from arcade_serve.fastapi import TaskTrackerMiddleware
from loguru import logger


class CustomUvicornServer(uvicorn.Server):
    """Uvicorn server with force quit support on double SIGINT/SIGTERM."""

    def __init__(self, config: uvicorn.Config, task_tracker: TaskTrackerMiddleware):
        super().__init__(config)
        self.task_tracker = task_tracker
        self._signal_count = 0

    def handle_exit(self, sig: int, frame: FrameType | None) -> None:
        """
        Handle termination signals with force quit on second signal.

        First signal (SIGINT/SIGTERM): Graceful shutdown
        Second signal: Force quit with os._exit(1)
        """
        self._signal_count += 1

        if self._signal_count == 1:
            logger.info("Shutting down gracefully. Press Ctrl+C again to force quit.")
            self.should_exit = True
        else:
            logger.warning("Force quit triggered - cancelling all active requests")
            cancelled = self.task_tracker.cancel_all_tasks()
            logger.info(f"Cancelled {cancelled} active request(s)")
            os._exit(1)
