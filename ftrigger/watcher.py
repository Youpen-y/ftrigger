"""File monitoring module

Monitors file system changes using watchdog
"""

import os
from logging import getLogger
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config import WatchConfig
from .executor import execute_claude, Permissions

logger = getLogger(__name__)


class WatchHandler(FileSystemEventHandler):
    """File change event handler"""

    def __init__(self, config: WatchConfig):
        super().__init__()
        self.config = config
        self._last_triggered = {}  # For simple debouncing

    def _should_process(self, event_path: str) -> bool:
        """Determine if the event should be processed

        Args:
            event_path: File path involved in the event

        Returns:
            Whether the event should be processed
        """
        # Check file extension
        if self.config.extensions:
            path = Path(event_path)
            if path.suffix not in self.config.extensions:
                logger.debug(f"Skipping non-target extension file: {event_path}")
                return False

        # Check exclude patterns
        if self.config.exclude_patterns:
            import fnmatch
            for pattern in self.config.exclude_patterns:
                # Check if any part of the path matches the pattern
                path_parts = Path(event_path).parts
                if any(fnmatch.fnmatch(part, pattern) for part in path_parts):
                    logger.debug(f"Skipping file matching exclude pattern '{pattern}': {event_path}")
                    return False
                # Also check full path
                if fnmatch.fnmatch(event_path, pattern) or pattern in event_path:
                    logger.debug(f"Skipping file matching exclude pattern '{pattern}': {event_path}")
                    return False

        # Skip temporary files (preserve default behavior)
        basename = os.path.basename(event_path)
        if basename.endswith("~") or basename.startswith("#"):
            logger.debug(f"Skipping temporary file: {event_path}")
            return False

        return True

    def _trigger_claude(self, file_path: str):
        """Trigger Claude CLI

        Args:
            file_path: Changed file path
        """
        # Format prompt (if {file} variable is used in configuration)
        prompt = self.config.prompt

        # Simple debouncing: only trigger once per file within 5 seconds
        import time

        now = time.time()
        last_time = self._last_triggered.get(file_path, 0)
        if now - last_time < 5:
            logger.debug(f"Debounce skip: {file_path}")
            return

        self._last_triggered[file_path] = now

        # Create permission parameters based on configuration
        perm_mode = self.config.permission_mode
        permissions = Permissions(
            auto=(perm_mode == "auto"),
            accept_edits=(perm_mode == "acceptEdits"),
            bypass_permissions=(perm_mode == "bypassPermissions"),
            dont_ask=(perm_mode == "dontAsk"),
        )

        execute_claude(prompt, file_path, permissions, self.config.allowed_tools)

    def on_created(self, event):
        """File creation event"""
        if event.is_directory:
            return

        # Ensure src_path is a string
        src_path = event.src_path if isinstance(event.src_path, str) else event.src_path.decode('utf-8')

        if self._should_process(src_path):
            logger.info(f"File created: {src_path}")
            self._trigger_claude(src_path)

    def on_modified(self, event):
        """File modification event"""
        if event.is_directory:
            return

        # Ensure src_path is a string
        src_path = event.src_path if isinstance(event.src_path, str) else event.src_path.decode('utf-8')

        if self._should_process(src_path):
            logger.info(f"File modified: {src_path}")
            self._trigger_claude(src_path)


def create_observer(config: WatchConfig) -> Observer:
    """Create observer for watch configuration

    Args:
        config: Watch configuration

    Returns:
        Configured Observer object
    """
    observer = Observer()
    handler = WatchHandler(config)
    observer.schedule(handler, config.path, recursive=config.recursive)
    return observer


def start_watchers(configs: list[WatchConfig]) -> list[Observer]:
    """Start all watchers

    Args:
        configs: List of watch configurations

    Returns:
        List of Observer objects
    """
    observers = []

    for config in configs:
        observer = create_observer(config)
        observer.start()
        observers.append(observer)
        logger.info(f"Started watch: {config.path} (recursive: {config.recursive})")

    return observers
