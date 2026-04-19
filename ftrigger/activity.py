"""Activity tracking module for ftrigger

Records and retrieves trigger activity statistics and history.
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from threading import Lock
from typing import Optional

from logging import getLogger

logger = getLogger(__name__)


class ActivityTracker:
    """Track trigger activities with persistent storage"""

    def __init__(self, instance_id: Optional[str] = None, storage_path: Optional[Path] = None):
        """Initialize activity tracker

        Args:
            instance_id: Instance identifier for per-instance tracking (e.g., "pid12345")
            storage_path: Path to store activity data. Defaults to ~/.config/ftrigger/activity.json
                          If instance_id is provided, uses activity.{instance_id}.json
        """
        self._lock = Lock()

        if storage_path is None:
            # Use user config directory
            if os.name == "nt":  # Windows
                config_dir = Path(os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming")))
            else:
                config_dir = Path(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")))

            # Use instance-specific file if instance_id is provided
            if instance_id:
                storage_path = config_dir / "ftrigger" / f"activity.{instance_id}.json"
            else:
                storage_path = config_dir / "ftrigger" / "activity.json"

        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing data or create new
        self._data = self._load()

    def _load(self) -> dict:
        """Load activity data from storage

        Returns:
            Activity data dictionary
        """
        if not self.storage_path.exists():
            return {"activities": []}

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "activities" not in data:
                    data["activities"] = []
                return data
        except Exception as e:
            logger.warning(f"Failed to load activity data: {e}")
            return {"activities": []}

    def set_instance_info(self, pid: int, config_path: str) -> None:
        """Set instance metadata

        Args:
            pid: Process ID
            config_path: Configuration file path
        """
        with self._lock:
            self._data["instance"] = {
                "pid": pid,
                "config": config_path,
            }
            self._save()

    def get_instance_info(self) -> Optional[dict]:
        """Get instance metadata

        Returns:
            Instance info dict or None
        """
        return self._data.get("instance")

    def _save(self) -> None:
        """Save activity data to storage"""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save activity data: {e}")

    def record(self, file_path: str, event_type: str, watch_path: str) -> None:
        """Record a trigger activity

        Args:
            file_path: Path to the file that triggered
            event_type: Type of event (created, modified, deleted, moved)
            watch_path: Watch configuration path that triggered
        """
        with self._lock:
            activity = {
                "timestamp": datetime.now().isoformat(),
                "date": date.today().isoformat(),
                "file_path": file_path,
                "event_type": event_type,
                "watch_path": watch_path,
            }

            self._data["activities"].append(activity)

            # Keep only last 1000 activities to prevent unbounded growth
            if len(self._data["activities"]) > 1000:
                self._data["activities"] = self._data["activities"][-1000:]

            self._save()

    def get_today_stats(self) -> dict:
        """Get today's activity statistics

        Returns:
            Dictionary with statistics (triggers, files, by event type)
        """
        with self._lock:
            today = date.today().isoformat()

            # Filter today's activities
            today_activities = [
                a for a in self._data["activities"]
                if a.get("date") == today
            ]

            # Count by event type
            stats = {
                "triggers": len(today_activities),
                "files": len(set(a["file_path"] for a in today_activities)),
                "created": 0,
                "modified": 0,
                "deleted": 0,
                "moved": 0,
            }

            for activity in today_activities:
                event_type = activity.get("event_type", "unknown")
                if event_type in stats:
                    stats[event_type] += 1

            return stats

    def get_recent_activities(self, limit: int = 10) -> list[dict]:
        """Get recent activities

        Args:
            limit: Maximum number of activities to return

        Returns:
            List of recent activities (most recent first)
        """
        with self._lock:
            # Get last N activities in reverse order
            recent = self._data["activities"][-limit:][::-1]

            # Parse timestamps for display
            result = []
            for activity in recent:
                try:
                    ts = datetime.fromisoformat(activity["timestamp"])
                    time_str = ts.strftime("%H:%M:%S")
                except:
                    time_str = activity.get("timestamp", "")[:8]

                result.append({
                    "time": time_str,
                    "file_path": activity["file_path"],
                    "event_type": activity.get("event_type", "unknown"),
                })

            return result


# Global tracker instances (support multiple instances)
_trackers: dict[str, ActivityTracker] = {}
_tracker_lock = Lock()


def get_tracker(instance_id: Optional[str] = None) -> ActivityTracker:
    """Get or create activity tracker instance

    Args:
        instance_id: Optional instance identifier (e.g., "pid12345").
                     If None, automatically uses current process PID.

    Returns:
        ActivityTracker instance
    """
    global _trackers

    with _tracker_lock:
        # Auto-detect instance_id from current PID if not provided
        if instance_id is None:
            import os
            instance_id = f"pid{os.getpid()}"

        if instance_id not in _trackers:
            _trackers[instance_id] = ActivityTracker(instance_id=instance_id)

        return _trackers[instance_id]
