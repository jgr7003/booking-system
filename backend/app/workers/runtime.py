"""Shared plumbing of the worker processes: logging and graceful shutdown."""

import asyncio
import logging
import signal


def configure_logging() -> None:
    """Logs with time, level and logger name to stderr."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def stop_on_signals() -> asyncio.Event:
    """Returns an event that is set on SIGTERM or SIGINT (`docker stop`, Ctrl+C).

    Returns:
        The event to pass to the worker loop.
    """
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    return stop
