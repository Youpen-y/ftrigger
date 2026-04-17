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
        help="Configuration file path (default: config.yaml)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show verbose logs",
    )

    args = parser.parse_args()

    # Start with default log level to record configuration loading process
    setup_logging("INFO")

    # Load configuration
    try:
        config = load_config(args.config)

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Configuration file error: {e}")
        sys.exit(1)

    # Set final log level based on config file and command line arguments
    # Command line -v flag has highest priority
    log_level = "DEBUG" if args.verbose else config.log_level
    setup_logging(log_level)

    logger.info("File Trigger starting...")
    logger.info(f"Successfully loaded configuration: {args.config}")
    logger.info(f"Log level: {config.log_level}")

    # Start watchers
    try:
        observers, handlers = start_watchers(config.watches)
        logger.info(f"Started {len(observers)} watcher(s)")

        # Setup signal handling for graceful shutdown
        running = True

        def signal_handler(signum, frame):
            nonlocal running
            logger.info(f"Received signal {signum}, shutting down...")
            running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Main loop
        logger.info("Monitoring running, press Ctrl+C to stop")
        while running:
            try:
                import time

                time.sleep(1)
            except KeyboardInterrupt:
                break

        # Stop all watchers and clean up resources
        logger.info("Stopping watchers...")

        # Stop observers first to prevent new events from entering
        for observer in observers:
            observer.stop()

        # Then cleanup pending timers after observers stopped
        for handler in handlers:
            handler.cleanup()

        # Finally join threads
        for observer in observers:
            observer.join()

        logger.info("File Trigger stopped")

    except Exception as e:
        logger.exception(f"Runtime error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
