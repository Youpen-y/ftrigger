"""Configuration management module

Loads and validates YAML configuration files from a single file.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from logging import getLogger

logger = getLogger(__name__)


@dataclass
class WatchConfig:
    """Single watch rule configuration"""

    path: str
    prompt: str
    recursive: bool = True
    extensions: Optional[list[str]] = None
    # Claude CLI permission configuration
    permission_mode: str = "default"  # auto, acceptEdits, bypassPermissions, default, dontAsk
    allowed_tools: Optional[list[str]] = None  # Allowed tools whitelist, e.g. ["Bash(git:*)", "Edit"]
    exclude_patterns: Optional[list[str]] = None  # Exclude path patterns, e.g. [".git", "node_modules", "*.log"]
    # Event filter: only listen to specified event types
    events: Optional[list[str]] = None  # ["created", "modified", "deleted", "moved"]

    # Supported event types
    SUPPORTED_EVENTS = {"created", "modified", "deleted", "moved"}

    def __post_init__(self):
        """Configuration validation"""
        # Validate path existence
        if not os.path.exists(self.path):
            raise ValueError(f"Watch path does not exist: {self.path}")

        # Normalize path
        self.path = os.path.abspath(self.path)

        # Determine if path is a directory or file
        self._is_directory = os.path.isdir(self.path)

        # Handle directory-specific options
        if not self._is_directory:
            # File mode: automatically ignore directory-related options
            if self.recursive:
                logger.warning(f"Path is a file ({self.path}), ignoring 'recursive' option")
                self.recursive = False

            if self.extensions:
                logger.warning(f"Path is a file ({self.path}), ignoring 'extensions' filter")
                self.extensions = None

        # Normalize extensions list (ensure starting with .)
        if self.extensions:
            self.extensions = [
                ext if ext.startswith(".") else f".{ext}"
                for ext in self.extensions
            ]

        # Validate permission mode
        valid_modes = ["auto", "acceptEdits", "bypassPermissions", "default", "dontAsk"]
        if self.permission_mode not in valid_modes:
            raise ValueError(f"Invalid permission mode: {self.permission_mode}, valid values are: {valid_modes}")

        # Check if prompt uses event type variables
        uses_event_type = "{events}" in self.prompt

        # Validate event types if provided
        if self.events is not None:
            # Reject empty list as configuration error
            if len(self.events) == 0:
                raise ValueError(
                    f"Empty 'events' list specified for watch at {self.path}. "
                    f"An empty events list will disable all file system monitoring. "
                    f"Either specify events to monitor or omit the field to use defaults. "
                    f"Supported events: {self.SUPPORTED_EVENTS}"
                )

            # Validate event type values
            invalid_events = set(self.events) - self.SUPPORTED_EVENTS
            if invalid_events:
                raise ValueError(
                    f"Invalid event types: {invalid_events}. "
                    f"Supported events: {self.SUPPORTED_EVENTS}"
                )
        else:
            # No events specified - use default behavior
            if uses_event_type:
                logger.warning(
                    f"Prompt uses '{{events}}' variable, "
                    f"but 'events' field is not specified for watch at {self.path}. "
                    f"Please specify which events to monitor. "
                    f"Supported events: {self.SUPPORTED_EVENTS}"
                )
            else:
                logger.debug(
                    f"No 'events' field specified for watch at {self.path}. "
                    f"Monitoring all supported events: {self.SUPPORTED_EVENTS}"
                )
            # Set default to all supported events if not specified
            self.events = list(self.SUPPORTED_EVENTS)

        logger.debug(f"Loaded watch config: path={self.path}, prompt='{self.prompt}', "
                    f"type={'directory' if self._is_directory else 'file'}, "
                    f"recursive={self.recursive}, extensions={self.extensions}, "
                    f"permission_mode={self.permission_mode}, allowed_tools={self.allowed_tools}, "
                    f"exclude_patterns={self.exclude_patterns}, events={self.events}")


@dataclass
class Config:
    """Global configuration"""

    log_level: str = "INFO"
    watches: list[WatchConfig] = field(default_factory=list)
    source_file: str = "unknown"  # Path to the configuration file

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create configuration object from dictionary"""
        log_level = data.get("log_level", "INFO")
        watches_data = data.get("watches", [])

        watches = []
        for watch_data in watches_data:
            try:
                watch = WatchConfig(
                    path=watch_data["path"],
                    prompt=watch_data["prompt"],
                    recursive=watch_data.get("recursive", True),
                    extensions=watch_data.get("extensions"),
                    permission_mode=watch_data.get("permission_mode", "default"),
                    allowed_tools=watch_data.get("allowed_tools"),
                    exclude_patterns=watch_data.get("exclude_patterns"),
                    events=watch_data.get("events"),
                )
                watches.append(watch)
            except KeyError as e:
                raise ValueError(f"Watch configuration missing required field: {e}")
            except ValueError as e:
                logger.warning(f"Skipping invalid watch configuration: {e}")

        # Require at least one watch
        if not watches:
            raise ValueError("Configuration must contain at least one watch rule")

        return cls(log_level=log_level, watches=watches)


def load_config_file(config_path: Path) -> Optional[dict]:
    """Load a single YAML configuration file.

    Args:
        config_path: Path to configuration file

    Returns:
        Parsed configuration data, or None if file doesn't exist or fails to load
    """
    if not config_path.exists():
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Failed to load config file {config_path}: {e}")
        return None


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from a single YAML file.

    Args:
        config_path: Path to configuration file. If None, uses "config.yaml" in current directory.

    Returns:
        Config object

    Raises:
        FileNotFoundError: Configuration file not found
        ValueError: Configuration file format error or invalid content
    """
    # Use default config path if not specified
    if config_path is None:
        config_path = "config.yaml"

    path = Path(config_path)

    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    if not path.is_file():
        raise ValueError(f"Configuration path must be a file: {config_path}")

    # Load YAML content
    data = load_config_file(path)
    if data is None:
        raise ValueError(f"Configuration file YAML parsing failed: {config_path}")

    if not data:
        raise ValueError("Configuration file is empty")

    # Parse and validate configuration
    try:
        config = Config.from_dict(data)
        # Set source file path for status display
        config.source_file = str(path.absolute())
        logger.debug(f"Loaded configuration from {config_path}: log_level={config.log_level}, watches={len(config.watches)}")
        return config
    except ValueError as e:
        raise ValueError(f"Configuration validation failed: {e}")
