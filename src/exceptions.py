# -*- coding: utf-8 -*-
"""
Defines custom exception classes and a decorator for handling exceptions
within the NZ Road Code Test Scraper application.

Provides a structured way to manage and log errors specific to different
components of the scraper (Browser, PageHandler, Extractor, DB, etc.).
"""

import inspect
from functools import wraps
from logging import Logger
from typing import Callable, Type, TypeVar


# === Base Exception ===
class NZRoadCodeTestError(Exception):
    """Base exception class for all custom errors raised by this application."""

    pass


# === Exception Handler Decorator ===
# Type variable for annotating the decorated function type
T = TypeVar("T", bound=Callable)


def exception_handler(
    error_cls: Type[Exception], logger: Logger, error_message: str = "Unexpected error occurred"
) -> Callable[[T], T]:
    """
    Decorate a function/method to catch standard exceptions and re-raise them as a specific custom error type.

    Logs the original exception details before re-raising. Handles both synchronous
    and asynchronous functions. Does not intercept exceptions that are already
    subclasses of NZRoadCodeTestError.

    :param error_cls: The custom exception class (subclass of NZRoadCodeTestError) to raise.
    :type error_cls: Type[Exception]
    :param logger: The logger instance to use for recording the exception.
    :type logger: Logger
    :param error_message: A prefix message for the log entry and the raised exception.
    :type error_message: str
    :return: A wrapper function that applies the exception handling logic.
    :rtype: Callable[[T], T]
    """

    def decorator(func: T) -> T:
        # Check if the decorated function is asynchronous
        if inspect.iscoroutinefunction(func):
            # Define an async wrapper for async functions
            @wraps(func)  # Preserve original function metadata (name, docstring)
            async def async_wrapper(*args, **kwargs):
                try:
                    # Execute the original async function
                    return await func(*args, **kwargs)
                except NZRoadCodeTestError:
                    # If it's already one of our custom errors, let it pass through
                    raise
                except Exception as e:
                    # Catch any other standard exception
                    log_msg = f"{error_message} in async function '{func.__name__}'"
                    logger.exception(log_msg)  # Log with stack trace
                    # Raise the specified custom error, chaining the original exception
                    raise error_cls(f"{log_msg}: {e}") from e

            # Return the async wrapper
            return async_wrapper  # type: ignore

        else:
            # Define a sync wrapper for regular functions
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    # Execute the original sync function
                    return func(*args, **kwargs)
                except NZRoadCodeTestError:
                    # If it's already one of our custom errors, let it pass through
                    raise
                except Exception as e:
                    # Catch any other standard exception
                    log_msg = f"{error_message} in function '{func.__name__}'"
                    logger.exception(log_msg)  # Log with stack trace
                    # Raise the specified custom error, chaining the original exception
                    raise error_cls(f"{log_msg}: {e}") from e

            # Return the sync wrapper
            return sync_wrapper  # type: ignore

    # Return the decorator itself
    return decorator


# === Component-Specific Exceptions ===
# Define specific error classes inheriting from the base or intermediate classes
# for better error categorization and handling.


# --- Browser Errors ---
class BrowserError(NZRoadCodeTestError):
    """Base class for errors related to browser operations (launching, context, etc.)."""

    pass


class BrowserInitializationError(BrowserError):
    """Raised specifically when browser initialization fails."""

    pass


class BrowserPageError(BrowserError):
    """Raised for errors occurring during page creation or interaction setup."""

    pass


# --- Page Handler Errors ---
class PageHandlerError(NZRoadCodeTestError):
    """Base class for errors related to page navigation and element interaction."""

    pass


class PageHandlerNavigationError(PageHandlerError):
    """Raised when navigating to a URL fails."""

    pass


class PageHandlerElementNotFoundError(PageHandlerError):
    """Raised when a required HTML element cannot be found on the page."""

    pass


# --- Image Downloader Errors ---
class ImageDownloaderError(NZRoadCodeTestError):
    """Raised for errors during image downloading or processing."""

    pass


# --- Extractor Errors ---
class ExtractorError(NZRoadCodeTestError):
    """Raised for errors during the data extraction process from page content."""

    pass


# --- Scraper Errors ---
class ScraperError(NZRoadCodeTestError):
    """Raised for errors in the main Scraper workflow orchestration."""

    pass


# --- DB Helper Errors ---
class DBHelperError(NZRoadCodeTestError):
    """Base class for errors related to database operations managed by DBHelper."""

    pass


class DBHelperInsertError(DBHelperError):
    """Raised specifically when database insertion fails within DBHelper."""

    pass


class DBHelperChapterExistsError(DBHelperError):
    """Raised specifically when attempting to insert a duplicate chapter ID (though currently handled in ChapterService)."""

    pass  # Note: This might be redundant if existence check is solid elsewhere.


# --- Chapter Service Errors ---
class ChapterServiceError(DBHelperError):
    """Base class for errors within the ChapterService layer (often related to DB interactions)."""

    # Inherits from DBHelperError as service errors often stem from DB issues.
    pass


class ChapterServiceInsertError(ChapterServiceError):  # Inherit from ChapterServiceError
    """Raised specifically when chapter insertion fails within the ChapterService."""

    pass
