# Copyright (C) 2024 Björn Gunnar Bryggman. Licensed under the MIT License.

"""
This module provides a utility function for configuring logging.

It sets up a logger with structured logging capabilities using the structlog library
and supports both console and file logging with different formats for each.
"""

import logging
import sys
from pathlib import Path

import structlog

# =============================================== #
#                 Main Function                   #
# =============================================== #


def init_logger(log_level: int, log_directory: Path) -> None:
    """
    Initialize a structured logger with console or file output.

    Process:
    -------
    -------
        - Configures structlog with shared processors for common logging information.
        - Sets up separate processors for console logging (human-friendly format) and file logging (JSON format).
        - Determines the output mode based on whether the standard error stream is a terminal.
        - If in a terminal, configures logging to the console with a human-readable format.
        - If not in a terminal, creates a log directory if it doesn't exist, configures logging to a file in JSON format.
        - Initializes structlog with the appropriate processors based on the output mode.

    Args:
    ----
    ----
        - log_level (int): The logging level to use (e.g., logging.INFO).
        - log_directory (Path): The directory where log files will be stored if file logging is used.

    Returns:
    -------
    -------
        - None.

    Exceptions:
    ----------
    ----------
        - OSError: If there's an issue creating the log directory or file.
    """
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S (UTC)"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # Processors for console logging (human-friendly format)
    console_processors = [*shared_processors, structlog.dev.ConsoleRenderer()]

    # Processors for file logging (JSON format)
    file_processors = [
        *shared_processors,
        structlog.processors.CallsiteParameterAdder({
            structlog.processors.CallsiteParameter.FUNC_NAME,
            structlog.processors.CallsiteParameter.LINENO,
            structlog.processors.CallsiteParameter.PROCESS,
        }),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(),
    ]

    if sys.stderr.isatty():
        logging.basicConfig(level=log_level, handlers=[logging.StreamHandler(sys.stdout)], format="%(message)s")

    else:
        log_directory.mkdir(parents=True, exist_ok=True)
        log_file_path = log_directory / "Log.txt"

        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(), foreign_pre_chain=shared_processors
            )
        )

        logging.basicConfig(level=log_level, handlers=[file_handler], format="%(message)s")

    structlog.configure(
        processors=console_processors if sys.stderr.isatty() else file_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
