"""File Trigger main entry point

Monitors file system changes and triggers Claude CLI tool
"""

import argparse
import logging
import signal
import sys

from logging import basicConfig, getLogger

from . import __version__
from .config import load_config
from .watcher import start_watchers

logger = getLogger(__name__)


def setup_logging(level: str = "INFO"):
    """Configure logging system

    Args:
        level: Log level
    """
    basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,  # Force reconfiguration even if already configured
    )


def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="File Trigger - Monitor file changes and trigger Claude CLI"
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.yaml",
        help="Configuration file path (default: config.yaml in current directory)",
    )
    parser.add_argument(
        "-s",
        "--status",
        action="store_true",
        help="Show status panel and exit",
    )
    parser.add_argument(
        "--pid",
        metavar="<pid|name>",
        help="Show detailed status for specified PID or service name (use with --status)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show verbose logs",
    )

    args = parser.parse_args()

    # For status mode, suppress config loading logs
    initial_log_level = "WARNING" if args.status else "INFO"
    setup_logging(initial_log_level)

    # Status mode: show status panel and exit
    if args.status:
        from .status import show_status_with_args

        # show_status_with_args handles pid argument internally
        show_status_with_args(args.pid)
        return

    # Load configuration for monitoring mode
    try:
        config = load_config(args.config)

    except FileNotFoundError as e:
        print(f"Configuration file not found: {args.config}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Please create a configuration file or specify a different path:", file=sys.stderr)
        print(f"  1. Create {args.config} in the current directory", file=sys.stderr)
        print(f"  2. Use -c to specify a config file: ftrigger -c /path/to/config.yaml", file=sys.stderr)
        print("", file=sys.stderr)
        print("Example configuration:", file=sys.stderr)
        print("  log_level: INFO", file=sys.stderr)
        print("  watches:", file=sys.stderr)
        print("    - path: /path/to/your/project", file=sys.stderr)
        print("      prompt: \"Review {file} for improvements.\"", file=sys.stderr)
        print("      recursive: true", file=sys.stderr)
        print("      extensions: [\".py\", \".js\"]", file=sys.stderr)
        print("      events: [\"created\", \"modified\"]", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Configuration file error: {e}", file=sys.stderr)
        sys.exit(1)

    # Set final log level based on config file and command line arguments
    # Command line -v flag has highest priority
    log_level = "DEBUG" if args.verbose else config.log_level
    setup_logging(log_level)

    print("File Trigger starting...")
    print(f"Configuration: {config.log_level} log level, {len(config.watches)} watch(es)")

    # Record instance info for activity tracking
    from .activity import get_tracker
    import os
    tracker = get_tracker()
    tracker.set_instance_info(os.getpid(), config.source_file)

    # Start watchers
    try:
        observers, handlers = start_watchers(config.watches)
        print(f"Started {len(observers)} watcher(s)")

        # Setup signal handling for graceful shutdown
        running = True

        def signal_handler(signum, frame):
            nonlocal running
            print(f"\nReceived signal {signum}, shutting down...")
            running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Main loop
        print("Monitoring running, press Ctrl+C to stop")
        while running:
            try:
                import time

                time.sleep(1)
            except KeyboardInterrupt:
                break

        # Stop all watchers and clean up resources
        print("Stopping watchers...")

        # Stop observers first to prevent new events from entering
        for observer in observers:
            observer.stop()

        # Then cleanup pending timers after observers stopped
        for handler in handlers:
            handler.cleanup()

        # Finally join threads with timeout to prevent indefinite hanging
        for observer in observers:
            observer.join(timeout=5)  # 5 second timeout per observer

        print("File Trigger stopped")

    except Exception as e:
        print(f"Runtime error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
