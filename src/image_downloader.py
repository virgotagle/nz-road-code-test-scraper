# -*- coding: utf-8 -*-
"""
Asynchronous image downloader module.

Provides functionality to download images from URLs and encode them
into base64 strings, suitable for embedding in databases or JSON.
Includes retry logic for network robustness.
"""

import asyncio
import base64  # For encoding binary image data

import aiohttp  # Asynchronous HTTP client library

from .config import NetworkConfig
from .exceptions import ImageDownloaderError, exception_handler
from .logging import get_logger

logger = get_logger(__name__)


class ImageDownloader:
    """
    Handles asynchronous downloading of images and encoding to base64.

    Uses aiohttp for efficient async network requests and includes configurable
    retry mechanisms defined in NetworkConfig.
    """

    def __init__(self, config: NetworkConfig = NetworkConfig()):
        """
        Initialize the ImageDownloader with network configuration.

        :param config: Network configuration settings (timeout, retries, etc.).
                       Defaults to a default NetworkConfig instance.
        :type config: NetworkConfig
        """
        self.config = config
        logger.debug("ImageDownloader initialized.")

    # Apply exception handler to catch unexpected errors during the download process
    @exception_handler(
        error_cls=ImageDownloaderError, logger=logger, error_message="Unexpected error downloading or encoding image"
    )
    async def download_to_base64(self, image_url: str) -> str:
        """
        Download an image from the given URL and return its base64 encoded representation.

        Attempts to download the image asynchronously using aiohttp. Implements a retry
        mechanism based on the configured `max_retries` and `retry_delay`.

        :param image_url: The URL of the image to download.
        :type image_url: str
        :return: A base64 encoded string representation of the downloaded image data.
        :rtype: str
        :raises ImageDownloaderError: If the download fails after all retry attempts or
                                      if an unexpected error occurs.
        """
        # Retry loop: attempts = number of retries + 1 initial try
        for attempt in range(1, self.config.max_retries + 2):
            try:
                logger.debug(f"Attempt {attempt}/{self.config.max_retries + 1}: Downloading image from {image_url}")

                # Create a new ClientSession for each attempt (or reuse if appropriate for many downloads)
                # Set timeout and SSL verification based on config
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
                    async with session.get(image_url, ssl=self.config.verify_ssl) as response:
                        # Raise an exception for bad status codes (4xx or 5xx)
                        response.raise_for_status()
                        # Read the response content (image data) as bytes
                        image_data = await response.read()

                logger.debug(f"Successfully downloaded {len(image_data)} bytes from {image_url}")
                # Encode the binary image data to base64 and decode to UTF-8 string
                base64_encoded = base64.b64encode(image_data).decode("utf-8")
                return base64_encoded

            except aiohttp.ClientError as e:
                # Catch client-side errors (network issues, DNS errors, bad status codes)
                logger.warning(f"Image download attempt {attempt} failed for {image_url}: {e}")
                # Check if more retries are allowed
                if attempt <= self.config.max_retries:
                    # Wait before the next retry
                    logger.debug(f"Waiting {self.config.retry_delay}s before next attempt...")
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    # If all retries failed, construct final error message and raise
                    error_msg = (
                        f"Failed to download image from {image_url} "
                        f"after {self.config.max_retries + 1} attempts: {e}"
                    )
                    logger.error(error_msg)
                    raise ImageDownloaderError(error_msg) from e
            # Note: The @exception_handler decorator will catch other unexpected exceptions
            # like asyncio.TimeoutError if it's not caught as ClientError, or base64 errors.

        # This point should theoretically not be reached due to the loop and exception handling,
        # but return an empty string or raise error if it somehow does.
        # Raising is better to indicate failure clearly.
        final_error_msg = f"Image download failed unexpectedly for {image_url} after all attempts."
        logger.error(final_error_msg)
        raise ImageDownloaderError(final_error_msg)
        # The type: ignore below was likely to suppress a potential mypy warning about
        # the function possibly not returning a value if the loop finished without returning or raising.
        # The explicit raise above makes this clearer.
        # -> str: # type: ignore
