"""Logs display module for ftrigger

Provides user-friendly log viewing functionality.
"""

import subprocess
import sys
from typing import Optional


def show_logs(
    follow: bool = False,
    last_n: Optional[int] = None,
    level: Optional[str] = None,
    grep: Optional[str] = None,
    unit: str = "ftrigger"
) -> None:
    """Display logs from journalctl.

    Args:
        follow: Enable follow mode (like tail -f)
        last_n: Number of recent lines to show
        level: Filter by log level (DEBUG, INFO, WARNING, ERROR)
        grep: Filter by keyword/pattern
        unit: Systemd unit name (default: ftrigger)
    """
    # Build journalctl command
    cmd = ["journalctl", "--user", "-u", unit]

    # Add follow mode
    if follow:
        cmd.append("-f")

    # Add line limit
    if last_n is not None:
        cmd.extend(["-n", str(last_n)])

    # Execute journalctl
    try:
        if follow or level or grep:
            # Need to process output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr to avoid blocking
                text=True
            )

            try:
                # Filter output line by line
                for line in process.stdout:
                    if _should_show_line(line, level, grep):
                        print(line, end='')
            finally:
                # Clean up resources
                process.stdout.close()
                process.wait()
        else:
            # Direct output, no filtering
            result = subprocess.run(cmd, capture_output=False, text=True)

    except FileNotFoundError:
        print(f"Error: journalctl not found. Are you running on Linux?", file=sys.stderr)
        print("For manual log viewing, use:", file=sys.stderr)
        print(f"  journalctl --user -u {unit}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully in follow mode
        print("\nLog viewing stopped.")
        sys.exit(0)


def _should_show_line(line: str, level: Optional[str], grep: Optional[str]) -> bool:
    """Check if a log line should be displayed based on filters.

    Args:
        line: Log line to check
        level: Log level filter (DEBUG, INFO, WARNING, ERROR)
        grep: Keyword filter

    Returns:
        True if line should be displayed, False otherwise
    """
    # Apply level filter
    if level:
        # Check if line contains the log level
        if level not in line:
            return False

    # Apply grep filter
    if grep:
        if grep not in line:
            return False

    return True
