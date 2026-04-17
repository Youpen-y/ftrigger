"""File monitoring module

Monitors file system changes using watchdog
"""

import os
import threading
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
        self._pending_timers = {}  # For delayed trigger strategy
        self._delay_seconds = 1  # Delay in seconds before triggering
        self._lock = threading.Lock()  # For thread-safe timer management

    def _should_handle_event(self, event_type: str) -> bool:
        """Check if the event type should be handled

        Args:
            event_type: Event type (created, modified, deleted, moved)

        Returns:
            True if the event should be handled, False otherwise
        """
        # If events list is empty, no events should be handled
        if not self.config.events:
            return False

        # Check if event type is in the configured list
        return event_type in self.config.events

    def _get_path(self, path) -> str:
        """Get normalized path string

        Args:
            path: Path object or string

        Returns:
            Normalized path string
        """
        if isinstance(path, bytes):
            return path.decode('utf-8')
        return path

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

    def _trigger_claude(self, file_path: str, event_type: str, **kwargs):
        """Trigger Claude CLI with delayed strategy

        Args:
            file_path: Changed file path
            event_type: Type of event (created, modified, deleted, moved)
            **kwargs: Additional event data (e.g., dest_path for moved events)

        Delayed trigger strategy:
        - When an event occurs, cancel any pending timer for the same file:event_type
        - Start a new timer to trigger after delay_seconds
        - If another event occurs before the timer fires, cancel and restart
        - This ensures only the final state triggers Claude after rapid changes
        """
        debounce_key = f"{file_path}:{event_type}"

        with self._lock:
            # Cancel existing timer if any
            if debounce_key in self._pending_timers:
                existing_timer = self._pending_timers[debounce_key]
                if existing_timer.is_alive():
                    existing_timer.cancel()
                    logger.debug(f"Cancelled pending trigger for: {file_path} ({event_type})")

            # Create a new delayed trigger
            timer = threading.Timer(
                self._delay_seconds,
                self._execute_trigger,
                args=(file_path, event_type, kwargs)
            )
            self._pending_timers[debounce_key] = timer
            timer.start()

            logger.debug(f"Scheduled delayed trigger for: {file_path} ({event_type}) in {self._delay_seconds}s")

    def _execute_trigger(self, file_path: str, event_type: str, kwargs: dict):
        """Actually execute Claude CLI trigger

        Args:
            file_path: Changed file path
            event_type: Type of event (created, modified, deleted, moved)
            kwargs: Additional event data (e.g., dest_path for moved events)
        """
        debounce_key = f"{file_path}:{event_type}"

        # Clean up pending timer (thread-safe)
        with self._lock:
            if debounce_key in self._pending_timers:
                del self._pending_timers[debounce_key]

        # Format prompt with event type variables
        prompt = self._format_prompt_with_event(
            self.config.prompt,
            event_type,
            file_path,
            **kwargs
        )

        # Create permission parameters based on configuration
        perm_mode = self.config.permission_mode
        permissions = Permissions(
            auto=(perm_mode == "auto"),
            accept_edits=(perm_mode == "acceptEdits"),
            bypass_permissions=(perm_mode == "bypassPermissions"),
            dont_ask=(perm_mode == "dontAsk"),
        )

        logger.info(f"Triggering Claude CLI: {prompt[:50]}...")
        execute_claude(prompt, file_path, permissions, self.config.allowed_tools)

    def _format_prompt_with_event(self, prompt: str, event_type: str, file_path: str, **kwargs) -> str:
        """Format prompt with event type and file path variables

        Args:
            prompt: Original prompt template
            event_type: Type of event (created, modified, deleted, moved)
            file_path: Path to the file
            **kwargs: Additional event data (e.g., dest_path for moved events)

        Returns:
            Formatted prompt
        """
        result = prompt

        # Replace event type variable
        result = result.replace("{events}", event_type)

        # Replace file path variables
        result = result.replace("{file}", file_path)
        result = result.replace("{path}", file_path)

        # Replace moved event specific variables
        if event_type == "moved" and "dest_path" in kwargs:
            dest_path = self._get_path(kwargs["dest_path"])
            result = result.replace("{dest_path}", dest_path)
            result = result.replace("{dest}", dest_path)
            # Also support src_path for moved events
            if "src_path" in kwargs:
                src_path = self._get_path(kwargs["src_path"])
                result = result.replace("{src_path}", src_path)
                result = result.replace("{src}", src_path)

        return result

    def _handle_event(self, event, event_type: str):
        """Handle generic file system event

        Args:
            event: File system event object
            event_type: Type of event (created, modified, deleted)
        """
        if not self._should_handle_event(event_type):
            return

        if event.is_directory:
            return

        path = self._get_path(event.src_path)

        if self._should_process(path):
            logger.info(f"File {event_type}: {path}")
            self._trigger_claude(path, event_type)

    def on_created(self, event):
        """File creation event"""
        self._handle_event(event, "created")

    def on_modified(self, event):
        """File modification event"""
        self._handle_event(event, "modified")

    def on_deleted(self, event):
        """File deletion event"""
        self._handle_event(event, "deleted")

    def on_moved(self, event):
        """File move/rename event"""
        if not self._should_handle_event("moved"):
            return

        if event.is_directory:
            return

        src_path = self._get_path(event.src_path)
        dest_path = self._get_path(event.dest_path)

        # Check if paths are within the watched directory
        src_in_watch = src_path.startswith(self.config.path)
        dest_in_watch = dest_path.startswith(self.config.path)

        # Apply file-level filtering (extensions, exclude patterns)
        # Only check filtering for paths that are within the watched directory
        process_src = src_in_watch and self._should_process(src_path)
        process_dest = dest_in_watch and self._should_process(dest_path)

        if not (process_src or process_dest):
            return

        # Determine which path to use for triggering based on the move scenario
        # - Move within watched dir: use dest_path (new location)
        # - Move out of watched dir: use src_path (old location, still relevant)
        # - Move into watched dir: use dest_path (new location in watched dir)
        if process_src and not process_dest:
            # File moved out of watched directory - use source path
            trigger_path = src_path
        elif process_dest and not process_src:
            # File moved into watched directory - use destination path
            trigger_path = dest_path
        else:
            # File moved within watched directory (renamed) - use destination path
            trigger_path = dest_path

        logger.info(f"File moved: {src_path} -> {dest_path}")
        self._trigger_claude(trigger_path, "moved", src_path=src_path, dest_path=dest_path)

    def cleanup(self):
        """Clean up pending timers and release resources

        This method should be called when stopping the watcher to ensure
        all pending timers are cancelled and resources are released properly.
        """
        with self._lock:
            for key, timer in list(self._pending_timers.items()):
                if timer.is_alive():
                    timer.cancel()
                    logger.debug(f"Cancelled pending timer during cleanup: {key}")
            self._pending_timers.clear()


def create_observer(config: WatchConfig) -> tuple[Observer, WatchHandler]:
    """Create observer for watch configuration

    Args:
        config: Watch configuration

    Returns:
        Tuple of (observer, handler) for the watch configuration
    """
    observer = Observer()
    handler = WatchHandler(config)
    observer.schedule(handler, config.path, recursive=config.recursive)
    return observer, handler


def start_watchers(configs: list[WatchConfig]) -> tuple[list[Observer], list[WatchHandler]]:
    """Start all watchers

    Args:
        configs: List of watch configurations

    Returns:
        Tuple of (list of Observer objects, list of WatchHandler objects)
    """
    observers = []
    handlers = []

    for config in configs:
        observer, handler = create_observer(config)
        observer.start()
        observers.append(observer)
        handlers.append(handler)
        logger.info(f"Started watch: {config.path} (recursive: {config.recursive})")

    return observers, handlers
