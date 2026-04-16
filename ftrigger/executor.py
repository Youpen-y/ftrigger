"""Claude CLI executor module

Responsible for building and executing claude -p commands
"""

import subprocess
import threading
from dataclasses import dataclass
from logging import getLogger
from typing import Optional

logger = getLogger(__name__)


@dataclass
class Permissions:
    """Claude CLI permission configuration

    Claude CLI uses --permission-mode parameter to control permission behavior.
    Available values:
    - auto: Auto mode, may require permission confirmation
    - acceptEdits: Automatically accept edit operations
    - bypassPermissions: Skip all permission checks (use with caution)
    - default: Default mode
    - dontAsk: Don't ask, automatically grant permissions
    """
    auto: bool = False
    accept_edits: bool = False
    bypass_permissions: bool = False
    dont_ask: bool = False

    def to_args(self) -> list[str]:
        """Convert to CLI arguments

        Returns:
            List of permission arguments
        """
        if self.bypass_permissions:
            return ["--dangerously-skip-permissions"]

        if self.auto:
            return ["--permission-mode", "auto"]

        if self.accept_edits:
            return ["--permission-mode", "acceptEdits"]

        if self.dont_ask:
            return ["--permission-mode", "dontAsk"]

        return []


def format_prompt(prompt: str, file_path: Optional[str] = None) -> str:
    """Format prompt with variable substitution support

    Args:
        prompt: Original prompt
        file_path: Changed file path (optional)

    Returns:
        Formatted prompt
    """
    variables = {}

    if file_path:
        variables["{file}"] = file_path
        variables["{path}"] = file_path

    # Replace all variables
    result = prompt
    for key, value in variables.items():
        result = result.replace(key, value)

    # Remove unreplaced variables if file_path is not provided
    if not file_path:
        result = result.replace("{file}", "").replace("{path}", "")

    return result.strip()


def execute_claude(
    prompt: str,
    file_path: Optional[str] = None,
    permissions: Optional[Permissions] = None,
    allowed_tools: Optional[list[str]] = None
) -> None:
    """Execute Claude CLI command asynchronously

    Args:
        prompt: Prompt to execute
        file_path: Changed file path (optional)
        permissions: Claude CLI permission configuration (optional)
        allowed_tools: Allowed tools whitelist (optional)
    """
    # Format prompt
    formatted_prompt = format_prompt(prompt, file_path)

    logger.info(f"Triggering Claude CLI: {formatted_prompt[:50]}...")

    # Build command
    cmd = ["claude"]

    # Add permission arguments
    if permissions:
        perm_args = permissions.to_args()
        if perm_args:
            cmd.extend(perm_args)
            logger.debug(f"Permission arguments: {' '.join(perm_args)}")

    # Add tools whitelist argument
    if allowed_tools:
        # Claude CLI supports comma or space separated tool list
        tools_str = ",".join(allowed_tools)
        cmd.extend(["--allowed-tools", tools_str])
        logger.debug(f"Tools whitelist: {tools_str}")

    # Add prompt argument
    cmd.extend(["-p", formatted_prompt])

    # Execute asynchronously in a new thread without blocking main thread
    def _run():
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                logger.info("Claude CLI executed successfully")
                if stdout:
                    # Use separators to make output clearer
                    logger.info("=" * 60)
                    logger.info("Claude response:")
                    logger.info("-" * 60)
                    # Output line by line to avoid overly long lines
                    for line in stdout.strip().split('\n'):
                        logger.info(f"  {line}")
                    logger.info("=" * 60)
            else:
                logger.error(f"Claude CLI execution failed (exit code: {process.returncode})")
                if stderr:
                    logger.error(f"Error: {stderr}")

        except FileNotFoundError:
            logger.error("claude command not found, please ensure Claude CLI is installed and in PATH")
        except Exception as e:
            logger.error(f"Error executing Claude CLI: {e}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
