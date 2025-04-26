# -*- coding: utf-8 -*-
"""
Logging setup module for the application.

Configures Python's standard logging library to provide consistent
log formatting, file rotation, and optional console output.
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler  # Handler for rotating log files
from typing import Optional


def setup_logging(
    log_dir: str = "assets/logs",  # Default directory for log files
    log_level: int = logging.DEBUG,  # Default logging level (captures DEBUG, INFO, WARNING, ERROR, CRITICAL)
    console_output: bool = True,  # Whether to also log to the console (stdout)
    max_bytes: int = 5 * 1024 * 1024,  # Max log file size: 5MB
    backup_count: int = 5,  # Number of old log files to keep
    log_format: Optional[str] = None,  # Optional custom log format string
) -> None:
    """
    Configure the root logger for the application.

    Sets up handlers for rotating file logging and optional console logging.
    Creates the log directory if it doesn't exist.

    :param log_dir: The directory where log files will be stored.
    :type log_dir: str
    :param log_level: The minimum logging level to capture (e.g., logging.INFO, logging.DEBUG).
    :type log_level: int
    :param console_output: If True, logs will also be sent to standard output.
    :type console_output: bool
    :param max_bytes: The maximum size (in bytes) a log file can reach before rotating.
    :type max_bytes: int
    :param backup_count: The number of backup log files to keep (e.g., app.log.1, app.log.2).
    :type backup_count: int
    :param log_format: A custom format string for log messages. If None, a default format is used.
                       See Python's logging documentation for format codes.
    :type log_format: Optional[str]
    """
    # Ensure the log directory exists
    os.makedirs(log_dir, exist_ok=True)

    # Create a log file name based on the current date
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"app_{today}.log")

    # Get the root logger instance. Configuring this affects all loggers unless they override settings.
    root_logger = logging.getLogger()
    # Set the minimum level for the root logger. Handlers can have higher levels.
    root_logger.setLevel(log_level)

    # Clear existing handlers attached to the root logger to avoid duplicate logs
    # if this function is called multiple times.
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Define the log message format
    formatter = logging.Formatter(
        log_format
        or "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        # Default format includes timestamp, level, logger name, and message
    )

    # --- File Handler Setup ---
    # Creates a handler that writes logs to a file, rotating it when it reaches max_bytes.
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"  # Specify encoding
    )
    file_handler.setFormatter(formatter)  # Apply the format to the handler
    file_handler.setLevel(log_level)  # Set the minimum level for this handler
    root_logger.addHandler(file_handler)  # Add the handler to the root logger

    # --- Console Handler Setup ---
    if console_output:
        # Creates a handler that writes logs to the console (standard output)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)  # Apply the format
        console_handler.setLevel(log_level)  # Set the minimum level
        root_logger.addHandler(console_handler)  # Add the handler

    # Log an initial message indicating logging is ready
    # Use the get_logger function to get a logger specific to this module
    get_logger(__name__).info(f"Logging initialized. Level: {logging.getLevelName(log_level)}. Log file: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Retrieve a logger instance with the specified name.

    This is a convenience function. Using `logging.getLogger(__name__)`
    in modules is standard practice, ensuring logger names correspond
    to module hierarchy.

    :param name: The name for the logger, typically the module's `__name__`.
    :type name: str
    :return: A Logger instance configured by the root logger setup.
    :rtype: logging.Logger
    """
    return logging.getLogger(name)
