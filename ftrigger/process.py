"""Process detection and status management module for ftrigger

Detects running ftrigger instances including systemd services and standalone processes.
"""

import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from logging import getLogger

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = getLogger(__name__)


@dataclass
class InstanceInfo:
    """ftrigger instance information"""

    pid: int
    type: str  # "service" | "standalone"
    name: str  # Service name or process identifier
    config_path: str
    start_time: Optional[datetime]
    status: str  # "running" | "stopped" | "unknown"
    watches_count: int = 0


def parse_systemd_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse systemd timestamp format.

    Args:
        timestamp_str: systemd timestamp string

    Returns:
        datetime object or None
    """
    if not timestamp_str or timestamp_str == "n/a":
        return None

    try:
        # systemd timestamp format: "Mon 2025-01-19 12:15:30 UTC" or "Mon 2025-01-19 12:15:30 CST"
        # or "2025-01-19 12:15:30" (without weekday prefix)

        # Remove weekday prefix (e.g., "Mon ", "Tue ", etc.)
        # Format is "DDD YYYY-MM-DD HH:MM:SS TZ" where DDD is 3-letter weekday
        parts = timestamp_str.split()
        if len(parts) >= 3 and len(parts[0]) == 3:
            # Has weekday prefix, remove it
            timestamp_str = ' '.join(parts[1:])

        # Remove timezone suffix (UTC, CST, etc.) if present
        parts = timestamp_str.rsplit(' ', 1)
        if len(parts) == 2 and parts[1] in ('UTC', 'CST', 'GMT', 'EST', 'PST', 'MST'):
            timestamp_str = parts[0]

        # Replace remaining space with T for ISO format
        timestamp_str = timestamp_str.replace(' ', 'T')

        return datetime.fromisoformat(timestamp_str)
    except (ValueError, AttributeError):
        logger.debug(f"Failed to parse timestamp: {timestamp_str}")
        return None


def _infer_config_path(service_name: str) -> str:
    """Infer config path from service name as fallback.

    Args:
        service_name: Service name (e.g., "ftrigger@dev.service")

    Returns:
        Inferred config path
    """
    if "@" in service_name:
        # Template service: ftrigger@dev -> ~/.config/ftrigger/dev.yaml
        instance_name = service_name.split("@")[1].replace(".service", "")
        return str(Path.home() / ".config" / "ftrigger" / f"{instance_name}.yaml")
    else:
        # Single instance service: ~/.config/ftrigger/config.yaml
        return str(Path.home() / ".config" / "ftrigger" / "config.yaml")


def get_systemd_services() -> list[InstanceInfo]:
    """Get systemd service status.

    Returns:
        List of InstanceInfo objects
    """
    instances = []

    # User service
    try:
        result = subprocess.run(
            ["systemctl", "--user", "show", "ftrigger.service"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        instance = parse_systemd_service(result.stdout, "ftrigger.service")
        if instance:
            instances.append(instance)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.debug(f"Failed to query user service: {e}")

    # Multi-instance services
    try:
        result = subprocess.run(
            ["systemctl", "--user", "list-units", "--type=service", "--all", "--plain"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        for line in result.stdout.split("\n"):
            if "ftrigger@" in line:
                # Parse service name
                parts = line.split()
                if parts:
                    service_name = parts[0].replace(".service", "")
                    try:
                        detail = subprocess.run(
                            ["systemctl", "--user", "show", service_name + ".service"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        instance = parse_systemd_service(detail.stdout, service_name + ".service")
                        if instance:
                            instances.append(instance)
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        continue

    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.debug(f"Failed to list template services: {e}")

    return instances


def parse_systemd_service(output: str, service_name: str) -> Optional[InstanceInfo]:
    """Parse systemctl show output to extract instance information.

    Args:
        output: systemctl show command output
        service_name: Service name

    Returns:
        InstanceInfo or None
    """
    properties = {}
    for line in output.split("\n"):
        if "=" in line:
            key, value = line.split("=", 1)
            properties[key] = value

    # Check if service is loaded
    load_state = properties.get("LoadState", "")
    if load_state == "not-found" or load_state == "masked":
        return None

    # Get PID
    main_pid = properties.get("MainPID", "0")
    try:
        pid = int(main_pid)
    except ValueError:
        pid = 0

    # Check if running
    active_state = properties.get("ActiveState", "unknown")
    if active_state == "active" and pid > 0:
        status = "running"
    elif active_state == "inactive":
        status = "stopped"
    else:
        status = "unknown"

    # Get start time
    start_time = parse_systemd_timestamp(properties.get("ExecMainStartTimestamp", ""))
    if not start_time:
        start_time = parse_systemd_timestamp(properties.get("ActiveEnterTimestamp", ""))

    # Extract config path from ExecStart command line
    config_path = properties.get("ExecStart", "")
    if config_path:
        # Remove quotes if present
        config_path = config_path.strip('"\'')

        # Extract -c or --config argument
        match = re.search(r'(?:--config[=\s]+|-[c][=\s]+)([^\s]+)', config_path)
        if match:
            config_path = match.group(1)
        else:
            # Fallback to inference
            config_path = _infer_config_path(service_name)
    else:
        # Fallback to inference
        config_path = _infer_config_path(service_name)

    return InstanceInfo(
        pid=pid,
        type="service",
        name=service_name,
        config_path=config_path,
        start_time=start_time,
        status=status,
    )


def get_standalone_processes(exclude_pids: Optional[set[int]] = None) -> list[InstanceInfo]:
    """Get standalone processes (cross-platform).

    Args:
        exclude_pids: PIDs to exclude (e.g., systemd service PIDs)

    Returns:
        List of instance information
    """
    if exclude_pids is None:
        exclude_pids = set()

    instances = []

    if HAS_PSUTIL:
        # Use psutil (cross-platform)
        for proc in psutil.process_iter(['pid', 'cmdline', 'create_time']):
            try:
                pid = proc.info['pid']
                if pid in exclude_pids:
                    continue

                cmdline = proc.info['cmdline']
                if not cmdline:
                    continue

                # Check if this is an ftrigger process
                cmdline_str = ' '.join(cmdline)
                if 'ftrigger' not in cmdline_str:
                    continue

                # Skip systemctl invocations
                if 'systemctl' in cmdline_str:
                    continue

                # Skip status query commands
                if '--status' in cmdline_str or (' -s' in cmdline_str and 'ftrigger' in cmdline_str):
                    continue

                # Extract config path from command line
                config_path = extract_config_from_command(cmdline_str)
                if not config_path:
                    config_path = "unknown"

                # Get start time
                start_time = None
                create_time = proc.info.get('create_time')
                if create_time:
                    try:
                        start_time = datetime.fromtimestamp(create_time)
                    except (ValueError, OSError):
                        pass

                instances.append(
                    InstanceInfo(
                        pid=pid,
                        type="standalone",
                        name=f"pid{pid}",
                        config_path=config_path,
                        start_time=start_time,
                        status="running",
                    )
                )

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    else:
        # Fallback to ps command (Linux/Unix only)
        if sys.platform == "win32":
            logger.debug("Process detection not supported on Windows without psutil")
            return []

        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            for line in result.stdout.split("\n"):
                if "ftrigger" in line and "grep" not in line:
                    parts = line.split(None, 10)
                    if len(parts) < 11:
                        continue

                    try:
                        pid = int(parts[1])
                    except (ValueError, IndexError):
                        continue

                    if pid in exclude_pids:
                        continue

                    command = parts[10]

                    if "systemctl" in command:
                        continue

                    if "--status" in command or " -s" in command.replace("ftrigger", ""):
                        continue

                    start_time = None
                    try:
                        time_result = subprocess.run(
                            ["ps", "-p", str(pid), "-o", "lstart="],
                            capture_output=True,
                            text=True,
                            timeout=2,
                        )
                        if time_result.stdout.strip():
                            start_time = datetime.strptime(time_result.stdout.strip(), "%a %b %d %H:%M:%S %Y")
                    except (ValueError, subprocess.TimeoutExpired):
                        pass

                    config_path = extract_config_from_command(command)
                    if not config_path:
                        config_path = "unknown"

                    # Try reading from /proc
                    if config_path == "unknown":
                        try:
                            with open(f"/proc/{pid}/cmdline", "r") as f:
                                cmdline = f.read().replace("\x00", " ")
                                config_path = extract_config_from_command(cmdline)
                        except (FileNotFoundError, PermissionError):
                            pass

                    instances.append(
                        InstanceInfo(
                            pid=pid,
                            type="standalone",
                            name=f"pid{pid}",
                            config_path=config_path,
                            start_time=start_time,
                            status="running",
                        )
                    )

        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.debug(f"Failed to query processes: {e}")

    return instances


def extract_config_from_command(command: str) -> str:
    """Extract config file path from command line.

    Args:
        command: Command line string

    Returns:
        Config file path, or "unknown" if not found
    """
    # Match --config or -c argument
    match = re.search(r"--config[=\s]+([^\s]+)|-c[=\s]+([^\s]+)", command)
    if match:
        config = match.group(1) or match.group(2)
        return config

    # Match directly passed YAML file
    match = re.search(r"([\w/~/\.\-]+\.yaml)", command)
    if match:
        return match.group(1)

    return "unknown"


def get_all_instances() -> list[InstanceInfo]:
    """Get all running instances.

    Returns:
        List of instance information
    """
    services = get_systemd_services()
    # Collect systemd service PIDs to avoid duplicate detection in standalone processes
    service_pids = {s.pid for s in services if s.pid > 0}
    standalones = get_standalone_processes(exclude_pids=service_pids)
    return services + standalones


def get_instance_by_pid(pid: int) -> Optional[InstanceInfo]:
    """Get instance info by PID.

    Args:
        pid: Process ID

    Returns:
        InstanceInfo or None
    """
    instances = get_all_instances()
    for inst in instances:
        if inst.pid == pid:
            return inst
    return None


def get_instance_by_name(name: str) -> Optional[InstanceInfo]:
    """Get instance info by name (supports service names).

    Args:
        name: Service name or "pid<number>"

    Returns:
        InstanceInfo or None
    """
    instances = get_all_instances()
    for inst in instances:
        if inst.name == name or inst.name == name + ".service":
            return inst

    # Try parsing as "pid123" format
    if name.startswith("pid"):
        try:
            pid = int(name[3:])
            for inst in instances:
                if inst.pid == pid:
                    return inst
        except ValueError:
            pass

    return None


def format_duration(start_time: datetime) -> str:
    """Format duration into a human-readable string.

    Args:
        start_time: Start time

    Returns:
        Formatted duration string
    """
    if not start_time:
        return "unknown"

    delta = datetime.now() - start_time

    if delta < timedelta(minutes=1):
        seconds = delta.seconds
        return f"{seconds} second{'s' if seconds != 1 else ''}"
    elif delta < timedelta(hours=1):
        minutes = delta.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif delta < timedelta(days=1):
        hours = delta.seconds // 3600
        mins = (delta.seconds % 3600) // 60
        if mins > 0:
            return f"{hours}h {mins}m"
        return f"{hours} hour{'s' if hours != 1 else ''}"
    else:
        days = delta.days
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{days}d {hours}h"
        return f"{days} day{'s' if days != 1 else ''}"


def shorten_path(path: str, max_len: int = 35) -> str:
    """Shorten path for display purposes.

    Args:
        path: File path
        max_len: Maximum length

    Returns:
        Shortened path
    """
    if not path or path == "unknown":
        return path

    if len(path) <= max_len:
        return path

    # Replace home directory with ~
    home = str(Path.home())
    if path.startswith(home):
        path = "~" + path[len(home):]

    if len(path) > max_len:
        # Keep beginning and end
        return path[:20] + "..." + path[-12:]

    return path
