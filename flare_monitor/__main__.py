"""Application entry point for Flare Monitor.

This module provides the main entry point when running the package as:
    python -m flare_monitor

It handles:
- Command-line argument parsing
- Logging configuration
- Configuration file loading
- Component initialization
- Graceful shutdown on Ctrl+C
- Proper error handling and exit codes

Example:
    # Run with default config
    python -m flare_monitor

    # Run with custom config
    python -m flare_monitor --config my-config.yaml

    # Run with debug logging
    python -m flare_monitor --log-level DEBUG
"""

import argparse
import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from flare_monitor.config import Config, load_config
from flare_monitor.monitor import MonitorManager
from flare_monitor.output import ConsoleOutputHandler


def setup_logging(
    config: Optional[Config] = None,
    cli_log_level: Optional[str] = None
) -> None:
    """Configure logging for the application.

    Sets up both console and file logging based on configuration.
    Console logging always goes to stderr, file logging is optional.

    Args:
        config: Configuration object with logging settings (optional)
        cli_log_level: Override log level from command line (optional)

    The log format includes timestamp, level, logger name, and message.
    Rotating file handler is used to prevent huge log files.
    """
    # Determine log level (CLI overrides config)
    if cli_log_level:
        log_level = getattr(logging, cli_log_level.upper())
    elif config and config.logging:
        log_level = getattr(logging, config.logging.level)
    else:
        log_level = logging.INFO

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Always add console handler (to stderr to avoid interfering with stdout)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if configured
    if config and config.logging and config.logging.output in ('file', 'both'):
        # Create log directory if it doesn't exist
        log_path = Path(config.logging.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        if config.logging.enable_rotation:
            file_handler = RotatingFileHandler(
                filename=config.logging.file_path,
                maxBytes=config.logging.max_file_size_mb * 1024 * 1024,
                backupCount=config.logging.backup_count,
                encoding='utf-8'
            )
        else:
            file_handler = logging.FileHandler(
                filename=config.logging.file_path,
                encoding='utf-8'
            )

        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        root_logger.info(f"Logging to file: {config.logging.file_path}")

    # Log the effective log level
    root_logger.info(f"Log level set to {logging.getLevelName(log_level)}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace with config and log_level attributes.

    The parser supports:
    - --config: Path to YAML configuration file
    - --log-level: Logging level override
    - --help: Show help message
    """
    parser = argparse.ArgumentParser(
        prog='flare_monitor',
        description='Flare Monitor - Real-time FXRP price monitoring and arbitrage detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m flare_monitor                              # Run with default config
  python -m flare_monitor --config my-config.yaml      # Use custom config
  python -m flare_monitor --log-level DEBUG            # Enable debug logging

For more information, see: https://github.com/your-repo/flare-monitor
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        metavar='FILE',
        help='Path to YAML configuration file (default: config/config.yaml)'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        metavar='LEVEL',
        help='Set logging level (overrides config file)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='Flare Monitor v0.1.0',
        help='Show version information and exit'
    )

    return parser.parse_args()


async def main() -> int:
    """Main application entry point.

    This is the async main function that orchestrates the entire application:
    1. Parse command-line arguments
    2. Set up initial logging (will be reconfigured after loading config)
    3. Load and validate configuration file
    4. Set up final logging configuration
    5. Initialize MonitorManager
    6. Create ConsoleOutputHandler
    7. Run the monitoring loop
    8. Handle shutdown gracefully

    Returns:
        Exit code: 0 for success, 1 for error

    The function catches all exceptions and ensures graceful shutdown,
    including proper cleanup of resources (Web3 connections, console display).
    """
    # Create output handler for early messages
    output = ConsoleOutputHandler()

    try:
        # Parse command-line arguments
        args = parse_args()

        # Set up basic logging (will be reconfigured after loading config)
        setup_logging(cli_log_level=args.log_level)

        logger = logging.getLogger("flare_monitor.main")
        logger.info("=" * 70)
        logger.info("Flare Monitor - Starting")
        logger.info("=" * 70)

        # Display startup banner
        output.console.print()
        output.console.print("[bold cyan]╔═══════════════════════════════════════════════════════╗[/bold cyan]")
        output.console.print("[bold cyan]║[/bold cyan]  [bold white]Flare Monitor - FXRP Price & Arbitrage Tracker[/bold white]  [bold cyan]║[/bold cyan]")
        output.console.print("[bold cyan]║[/bold cyan]  [dim]Version 0.1.0 - Monitoring Flare Network DEXes[/dim]    [bold cyan]║[/bold cyan]")
        output.console.print("[bold cyan]╚═══════════════════════════════════════════════════════╝[/bold cyan]")
        output.console.print()

        # Load configuration
        logger.info(f"Loading configuration from: {args.config}")
        output.print_info(f"Loading configuration from: {args.config}")

        try:
            config = load_config(args.config)
            logger.info("Configuration loaded successfully")
            output.print_success("Configuration loaded and validated")
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {e}")
            output.print_error(
                f"Configuration file not found: {args.config}",
                Exception(
                    "Please copy config/config.example.yaml to config/config.yaml "
                    "and customize it for your needs."
                )
            )
            return 1
        except ValueError as e:
            logger.error(f"Configuration validation failed: {e}")
            output.print_error("Configuration validation failed", e)
            return 1
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}", exc_info=True)
            output.print_error("Failed to load configuration", e)
            return 1

        # Reconfigure logging with settings from config file
        setup_logging(config=config, cli_log_level=args.log_level)

        # Log configuration summary
        logger.info(f"Monitoring {len([d for d in config.dexes if d.enabled])} DEXes: "
                   f"{', '.join(d.name for d in config.dexes if d.enabled)}")
        logger.info(f"Tracking {len([p for p in config.pairs if p.enabled])} pairs: "
                   f"{', '.join(f'{p.base}/{p.quote}' for p in config.pairs if p.enabled)}")
        logger.info(f"Poll interval: {config.monitoring.poll_interval_seconds}s")
        logger.info(f"Spread alert threshold: {config.monitoring.spread_alert_threshold_percent}%")
        logger.info(f"RPC endpoint: {config.flare.rpc_endpoints[0]}")

        # Display configuration summary
        output.console.print()
        output.console.print(f"[cyan]DEXes:[/cyan] {', '.join(d.name for d in config.dexes if d.enabled)}")
        output.console.print(f"[cyan]Pairs:[/cyan] {', '.join(f'{p.base}/{p.quote}' for p in config.pairs if p.enabled)}")
        output.console.print(f"[cyan]Poll Interval:[/cyan] {config.monitoring.poll_interval_seconds}s")
        output.console.print(f"[cyan]Spread Threshold:[/cyan] {config.monitoring.spread_alert_threshold_percent}%")
        output.console.print()

        # Initialize MonitorManager
        logger.info("Initializing Monitor Manager...")
        output.print_info("Initializing connection to Flare Network...")

        try:
            manager = MonitorManager(config)
            await manager.initialize()
            logger.info("Monitor Manager initialized successfully")
            output.print_success(
                f"Connected to Flare Network (Chain ID: {config.flare.chain_id})"
            )
        except ConnectionError as e:
            logger.error(f"Failed to connect to Flare Network: {e}")
            output.print_error(
                "Failed to connect to Flare Network RPC endpoint",
                Exception(
                    f"Could not connect to any RPC endpoint. Please check your internet "
                    f"connection and RPC configuration.\n"
                    f"Tried: {', '.join(config.flare.rpc_endpoints)}"
                )
            )
            return 1
        except ValueError as e:
            logger.error(f"Initialization failed: {e}")
            output.print_error("Initialization failed", e)
            return 1
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}", exc_info=True)
            output.print_error("Failed to initialize Monitor Manager", e)
            return 1

        # Display ready message
        output.console.print()
        output.print_success("Flare Monitor initialized successfully")
        output.print_info("Starting price monitoring... (Press Ctrl+C to stop)")
        output.console.print()
        logger.info("Starting monitoring loop...")

        # Short delay for user to read messages
        await asyncio.sleep(2)

        # Run the monitoring loop
        try:
            await manager.run_monitoring_loop()
        except KeyboardInterrupt:
            # This is caught in the monitoring loop, but handle it here too
            logger.info("Received keyboard interrupt signal")
            output.console.print()
            output.print_info("Shutdown signal received...")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)
            output.print_error("Fatal error in monitoring loop", e)
            raise

        # Graceful shutdown
        logger.info("Shutting down gracefully...")
        output.console.print()
        output.print_info("Shutting down Monitor Manager...")

        # Stop the manager if it's still running
        if manager.is_running:
            await manager.stop()

        # Display summary statistics
        logger.info("Generating shutdown summary...")

        # Count total prices and spreads processed
        total_dexes = len(manager.dex_statuses)
        online_dexes = sum(1 for status in manager.dex_statuses.values() if status.is_online)

        output.console.print()
        output.console.print("[bold cyan]═══ Shutdown Summary ═══[/bold cyan]")
        output.console.print(f"[cyan]DEX Status:[/cyan] {online_dexes}/{total_dexes} online at shutdown")

        # Show any DEXes that had errors
        offline_dexes = [
            name for name, status in manager.dex_statuses.items()
            if not status.is_online
        ]
        if offline_dexes:
            output.console.print(f"[yellow]Offline DEXes:[/yellow] {', '.join(offline_dexes)}")

        output.console.print()
        output.print_success("Flare Monitor shutdown complete")
        logger.info("Shutdown complete")

        return 0

    except KeyboardInterrupt:
        # Handle Ctrl+C at any point
        try:
            logger = logging.getLogger("flare_monitor.main")
            logger.info("Keyboard interrupt received during startup")
        except:
            pass
        output.console.print()
        output.print_warning("Startup interrupted by user")
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        # Catch any unexpected errors
        try:
            logger = logging.getLogger("flare_monitor.main")
            logger.error(f"Unexpected error in main: {e}", exc_info=True)
        except:
            pass
        output.console.print()
        output.print_error("Fatal error", e)
        return 1

    finally:
        # Ensure output handler is cleaned up
        try:
            output.stop_live_display()
        except Exception:
            pass  # Ignore errors during cleanup

        # Final log message
        try:
            logger = logging.getLogger("flare_monitor.main")
            logger.info("=" * 70)
            logger.info("Flare Monitor - Stopped")
            logger.info("=" * 70)
        except:
            pass


if __name__ == "__main__":
    # Run the async main function
    # Use asyncio.run() which handles event loop creation and cleanup
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        # Handle Ctrl+C during event loop setup
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        # Handle any unexpected errors
        print(f"\nFatal error: {e}", file=sys.stderr)
        sys.exit(1)
