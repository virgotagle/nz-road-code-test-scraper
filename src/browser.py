# -*- coding: utf-8 -*-
"""
Provides a simplified interface for managing Playwright browser instances asynchronously.

This module abstracts the setup and teardown of Playwright browsers, contexts,
and pages, offering a clean async context manager for obtaining a ready-to-use Page object.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional

from playwright.async_api import Browser as PlaywrightBrowser  # Alias to avoid naming conflict
from playwright.async_api import BrowserContext, Page, ViewportSize, async_playwright

from .config import BrowserType
from .exceptions import BrowserError, NZRoadCodeTestError
from .logging import get_logger

logger = get_logger(__name__)


class Browser:
    """
    Manages the lifecycle of a Playwright browser instance asynchronously.

    Provides an async context manager `page()` to easily get a configured browser page.
    Handles initialization, context creation, page creation, and cleanup.
    """

    def __init__(
        self,
        browser_type: BrowserType = BrowserType.CHROMIUM,
        headless: bool = True,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        user_agent: Optional[str] = None,
        default_timeout: int = 30000,  # Default timeout in milliseconds (30 seconds)
        slow_mo: int = 0,  # Default slow motion delay in milliseconds
        extra_args: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the browser configuration settings.

        :param browser_type: The type of browser to use (chromium, firefox, webkit).
        :type browser_type: BrowserType
        :param headless: Whether to run the browser in headless mode (no visible UI).
        :type headless: bool
        :param viewport_width: The width of the browser viewport.
        :type viewport_width: int
        :param viewport_height: The height of the browser viewport.
        :type viewport_height: int
        :param user_agent: Custom user agent string. If None, Playwright's default is used.
        :type user_agent: Optional[str]
        :param default_timeout: Default timeout for Playwright actions in milliseconds.
        :type default_timeout: int
        :param slow_mo: Delay (in ms) between Playwright operations. Useful for debugging.
        :type slow_mo: int
        :param extra_args: Additional arguments to pass to the browser launch method.
        :type extra_args: Optional[Dict[str, Any]]
        """
        self.browser_type = browser_type
        self.headless = headless
        self.viewport: ViewportSize = {
            "width": viewport_width,
            "height": viewport_height,
        }
        self.user_agent = user_agent
        self.default_timeout = default_timeout
        self.slow_mo = slow_mo
        self.extra_args = extra_args or {}  # Ensure extra_args is a dict

        logger.debug(f"Browser initialized: {self.browser_type.value} (headless={self.headless})")

    @asynccontextmanager
    async def page(self) -> AsyncIterator[Page]:
        """
        Provide a Playwright Page object within an asynchronous context manager.

        Handles the creation and cleanup of Playwright instance, browser, context, and page.

        :yield: A configured Playwright Page object.
        :rtype: AsyncIterator[Page]
        :raises BrowserError: If any stage of browser setup fails.
        :raises NZRoadCodeTestError: If a specific NZRoadCodeTestError occurs during setup.
        """
        playwright = None
        browser = None
        context = None
        page_instance = None  # Renamed to avoid conflict with yield variable name

        try:
            # Start Playwright process
            playwright = await self._start_playwright()
            # Launch the specified browser type
            browser = await self._launch_browser(playwright)
            # Create a new browser context with configured options
            context = await self._create_context(browser)
            # Create a new page within the context
            page_instance = await self._new_page(context)
            # Yield the page to the caller
            yield page_instance
        except NZRoadCodeTestError:
            # Don't wrap custom errors that are already specific
            raise
        except Exception as e:
            # Catch any unexpected exceptions during setup
            logger.error("Unexpected error during browser page setup", exc_info=True)
            raise BrowserError("Unexpected error during browser page setup") from e
        finally:
            # Ensure cleanup happens regardless of success or failure
            await self._cleanup(context, browser, playwright)

    async def _start_playwright(self):
        """Start the Playwright async context manager."""
        logger.debug("Starting Playwright")
        # Start the main Playwright instance
        return await async_playwright().start()

    async def _launch_browser(self, playwright) -> PlaywrightBrowser:
        """
        Launch a browser instance using the configured type and options.

        :param playwright: The active Playwright instance.
        :type playwright: Playwright
        :return: The launched Playwright Browser instance.
        :rtype: PlaywrightBrowser
        :raises BrowserError: If the browser type is unsupported or launch fails.
        """
        try:
            # Get the appropriate launch method based on browser_type (e.g., playwright.chromium)
            browser_launcher = getattr(playwright, self.browser_type.value, None)
            if not browser_launcher:
                raise BrowserError(f"Unsupported browser type: {self.browser_type.value}")

            logger.info(f"Launching browser: {self.browser_type.value} (headless={self.headless})")
            # Launch the browser with configured options
            return await browser_launcher.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
                **self.extra_args,  # Pass any extra arguments
            )
        except Exception as e:
            # Catch potential errors during launch (e.g., browser not installed)
            raise BrowserError(f"Failed to launch browser: {self.browser_type.value}") from e

    async def _create_context(self, browser: PlaywrightBrowser) -> BrowserContext:
        """
        Create a new browser context with specific settings.

        :param browser: The active Playwright Browser instance.
        :type browser: PlaywrightBrowser
        :return: The created BrowserContext instance.
        :rtype: BrowserContext
        :raises BrowserError: If context creation fails.
        """
        try:
            # Create a new isolated browser context
            context = await browser.new_context(
                viewport=self.viewport,
                user_agent=self.user_agent,
            )
            # Set the default timeout for operations within this context
            context.set_default_timeout(self.default_timeout)
            logger.info("Browser context created")
            return context
        except Exception as e:
            # Catch potential errors during context creation
            raise BrowserError("Failed to create browser context") from e

    async def _new_page(self, context: BrowserContext) -> Page:
        """
        Create a new page within the given browser context.

        :param context: The active BrowserContext instance.
        :type context: BrowserContext
        :return: The created Page instance.
        :rtype: Page
        :raises BrowserError: If page creation fails.
        """
        try:
            # Open a new tab/page in the context
            page = await context.new_page()
            logger.info("New browser page created")
            return page
        except Exception as e:
            # Catch potential errors during page creation
            raise BrowserError("Failed to create new page") from e

    async def _cleanup(self, context, browser, playwright):
        """
        Clean up Playwright resources (context, browser, instance).

        Attempts to close resources gracefully and logs warnings on errors.

        :param context: The BrowserContext instance to close (if exists).
        :type context: Optional[BrowserContext]
        :param browser: The PlaywrightBrowser instance to close (if exists).
        :type browser: Optional[PlaywrightBrowser]
        :param playwright: The Playwright instance to stop (if exists).
        :type playwright: Optional[Playwright]
        """
        # Close resources in reverse order of creation
        try:
            if context:
                logger.debug("Closing browser context")
                await context.close()
            if browser:
                logger.debug("Closing browser instance")
                await browser.close()
            if playwright:
                logger.debug("Stopping Playwright")
                await playwright.stop()
            logger.info("Browser cleanup complete")
        except Exception:
            # Log cleanup errors but don't raise, as the main operation might have succeeded
            logger.warning("Error during browser cleanup", exc_info=True)
