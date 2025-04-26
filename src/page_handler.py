# -*- coding: utf-8 -*-
"""
Module responsible for handling browser page interactions and navigation.

Provides methods to perform common actions on the NZ Road Code test website,
such as navigating to pages, clicking buttons (start, next, finish),
interacting with accordions, and selecting answers. It encapsulates
Playwright page operations and includes error handling and waits.
"""

import logging

from playwright.async_api import Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError  # Alias to avoid confusion

from .config import ROAD_CODE_TEST_URL  # Base URL for the test section

# Import specific exceptions for better error context
from .exceptions import PageHandlerElementNotFoundError, PageHandlerError, PageHandlerNavigationError, exception_handler

logger = logging.getLogger(__name__)


class PageHandler:
    """
    Encapsulates Playwright page interactions for the Road Code Test website.

    Provides high-level methods for common user actions like navigation,
    starting/finishing tests, answering questions, and handling dynamic elements.
    """

    # Default timeouts and waits for page interactions (in milliseconds)
    DEFAULT_TIMEOUT = 5000  # Timeout for waiting for elements to appear/be clickable
    DEFAULT_WAIT = 1000  # Short delay after actions to allow UI updates

    def __init__(self, page: Page):
        """
        Initialize the PageHandler with an active Playwright Page object.

        :param page: The Playwright Page instance to interact with.
        :type page: Page
        """
        self.page = page
        logger.debug("PageHandler initialized.")

    async def wait_for_page_ready(self, timeout: int = DEFAULT_TIMEOUT, wait_after: int = DEFAULT_WAIT) -> None:
        """
        Wait for the page's body element to be visible, indicating basic readiness.

        Also adds a configurable small delay afterwards to allow for potential
        JavaScript execution or rendering updates.

        :param timeout: Maximum time (ms) to wait for the body element.
        :type timeout: int
        :param wait_after: Time (ms) to pause after the body is visible.
        :type wait_after: int
        :raises PageHandlerError: If the body element doesn't become visible within the timeout.
        """
        try:
            logger.debug(f"Waiting up to {timeout}ms for page body to be visible.")
            # Wait for the 'body' element to be in a visible state
            await self.page.locator("body").wait_for(state="visible", timeout=timeout)
            logger.debug(f"Page body visible. Waiting additional {wait_after}ms.")
            # Add a small fixed delay
            await self.page.wait_for_timeout(wait_after)
        except PlaywrightTimeoutError as e:
            msg = f"Page body did not become visible within {timeout}ms."
            logger.error(msg)
            raise PageHandlerError(msg) from e
        except Exception as e:
            logger.exception("Unexpected error while waiting for page ready state.")
            raise PageHandlerError("Unexpected error waiting for page ready") from e

    @exception_handler(PageHandlerNavigationError, logger, "Navigation failed")
    async def goto_road_code_page(self) -> None:
        """
        Navigate the browser page to the main NZ Road Code test landing page.

        Waits for the page to be ready after navigation.

        :raises PageHandlerNavigationError: If navigation fails (e.g., network error, invalid URL).
        """
        target_url = ROAD_CODE_TEST_URL
        logger.info(f"Navigating to main Road Code page: {target_url}")
        try:
            await self.page.goto(target_url)
            # Wait for the page to settle after navigation
            await self.wait_for_page_ready()
            logger.info(f"Navigation to {target_url} successful.")
        except Exception as e:
            # The decorator will catch and wrap this
            logger.error(f"Failed to navigate to {target_url}")
            raise  # Re-raise for the decorator

    @exception_handler(PageHandlerNavigationError, logger, "Navigation failed")
    async def goto_road_code_test(self, test_url: str) -> None:
        """
        Navigate the browser page to a specific Road Code test chapter URL.

        Waits for the page to be ready after navigation.

        :param test_url: The absolute URL of the specific test chapter page.
        :type test_url: str
        :raises PageHandlerNavigationError: If navigation fails.
        """
        logger.info(f"Navigating to specific test URL: {test_url}")
        try:
            await self.page.goto(test_url)
            # Wait for the page to settle
            await self.wait_for_page_ready()
            logger.info(f"Navigation to {test_url} successful.")
        except Exception as e:
            # The decorator will catch and wrap this
            logger.error(f"Failed to navigate to {test_url}")
            raise  # Re-raise for the decorator

    @exception_handler(PageHandlerError, logger, "Failed clicking accordions")
    async def click_road_code_test_accordions(self) -> None:
        """
        Find and click all collapsed (inactive) accordion elements on the current page.

        Used on the main landing page to reveal links to all test chapters.

        :raises PageHandlerError: If finding or clicking accordions fails.
        """
        logger.debug("Expanding inactive accordions on the page.")
        # Selector targets accordion divs that have the 'accordion--inactive' class
        selector = "div.accordion.layout--container.layout--nopadding.accordion--inactive"
        try:
            accordions = await self.page.query_selector_all(selector)
            logger.debug(f"Found {len(accordions)} inactive accordions to click.")
            if not accordions:
                logger.warning("No inactive accordions found using selector: {selector}")
                return  # Nothing to click

            for i, accordion in enumerate(accordions):
                logger.debug(f"Clicking inactive accordion {i+1}/{len(accordions)}")
                await accordion.click()
                # Optional: Add a small delay between clicks if needed
                # await self.page.wait_for_timeout(100)
            logger.info("Finished clicking all found inactive accordions.")
        except Exception as e:
            # The decorator will catch and wrap this
            logger.error(f"Error occurred while clicking accordions with selector '{selector}'.")
            raise  # Re-raise for the decorator

    @exception_handler(PageHandlerError, logger)  # Generic handler, specific errors raised inside
    async def _click_if_visible(
        self, locator: Locator, operation_name: str, retries: int = 1, timeout: int = DEFAULT_TIMEOUT
    ) -> None:
        """
        Internal helper to reliably click an element located by a Playwright Locator.

        Waits for the element to be visible within a timeout period before clicking.
        Includes optional retries with delays.

        :param locator: The Playwright Locator for the target element.
        :type locator: Locator
        :param operation_name: A descriptive name for the operation (e.g., "Start button") for logging.
        :type operation_name: str
        :param retries: Number of additional attempts if the element is not visible initially.
        :type retries: int
        :param timeout: Time (ms) to wait for visibility in each attempt.
        :type timeout: int
        :raises PageHandlerElementNotFoundError: If the element is not visible after all attempts.
        :raises PageHandlerError: For other unexpected errors during the click operation.
        """
        # Total attempts = 1 initial try + number of retries
        for attempt in range(retries + 1):
            try:
                logger.debug(f"Attempt {attempt + 1}: Waiting for '{operation_name}' to be visible...")
                # Wait for the element matched by the locator to be visible
                await locator.wait_for(state="visible", timeout=timeout)
                logger.debug(f"'{operation_name}' is visible. Clicking...")
                # Perform the click action
                await locator.click()
                logger.debug(f"'{operation_name}' clicked successfully on attempt {attempt + 1}.")
                return  # Success, exit the loop and method
            except PlaywrightTimeoutError as e:
                # Element was not visible within the timeout for this attempt
                logger.warning(f"'{operation_name}' not visible within {timeout}ms on attempt {attempt + 1}.")
                if attempt == retries:
                    # If this was the last attempt, raise a specific error
                    msg = f"Element '{operation_name}' not visible after {retries + 1} attempts."
                    logger.error(msg)
                    raise PageHandlerElementNotFoundError(msg) from e
                else:
                    # If more retries are available, wait before the next attempt
                    logger.debug(f"Retrying after {self.DEFAULT_WAIT}ms wait...")
                    await self.page.wait_for_timeout(self.DEFAULT_WAIT)
            except Exception as e:
                # Catch any other unexpected error during wait_for or click
                msg = f"Unexpected error during click operation for '{operation_name}' on attempt {attempt + 1}"
                logger.exception(msg)  # Log with stack trace
                # Raise a generic PageHandlerError, preserving the original exception
                raise PageHandlerError(f"{msg}: {e}") from e

    @exception_handler(PageHandlerError, logger, "Failed attempting to start test")
    async def start_road_code_test(self) -> None:
        """
        Find and click the 'Start' button to begin a test chapter.

        Uses the reliable `_click_if_visible` helper.

        :raises PageHandlerElementNotFoundError: If the start button cannot be found.
        :raises PageHandlerError: For other interaction errors.
        """
        logger.info("Attempting to click the 'Start' button.")
        # Locate the start button, typically an anchor tag <a> containing the text "Start"
        start_button_locator = self.page.locator("a").filter(has_text="Start")
        await self._click_if_visible(start_button_locator, "Start button")
        logger.info("Start button clicked.")
        # Add a small pause after clicking start
        await self.page.wait_for_timeout(self.DEFAULT_WAIT)

    @exception_handler(PageHandlerError, logger, "Failed attempting to click answer")
    async def click_answer(self, answer_text: str) -> None:
        """
        Find and click the answer choice matching the provided text exactly.

        Uses the reliable `_click_if_visible` helper.

        :param answer_text: The exact text of the answer option to click.
        :type answer_text: str
        :raises PageHandlerElementNotFoundError: If the answer button cannot be found.
        :raises PageHandlerError: For other interaction errors.
        """
        logger.info(f"Attempting to click answer: '{answer_text[:50]}...'")  # Log truncated answer
        # Locate the element containing the exact answer text. This might be a button, div, etc.
        # Using get_by_text is generally robust.
        answer_locator = self.page.get_by_text(answer_text, exact=True)
        await self._click_if_visible(answer_locator, f"Answer '{answer_text[:30]}...'")
        logger.info(f"Clicked answer: '{answer_text[:50]}...'")
        # Add a small pause after clicking an answer
        await self.page.wait_for_timeout(self.DEFAULT_WAIT)

    @exception_handler(PageHandlerError, logger, "Failed attempting to click next question")
    async def next_question(self) -> None:
        """
        Find and click the 'Next question' button to proceed in the test.

        Uses the reliable `_click_if_visible` helper.

        :raises PageHandlerElementNotFoundError: If the next button cannot be found.
        :raises PageHandlerError: For other interaction errors.
        """
        logger.info("Attempting to click the 'Next question' button.")
        # Locate the next question button, typically an anchor tag <a>
        next_button_locator = self.page.locator("a").filter(has_text="Next question")
        await self._click_if_visible(next_button_locator, "Next question button")
        logger.info("Next question button clicked.")
        # Wait after clicking next to allow the next question to load
        await self.page.wait_for_timeout(self.DEFAULT_WAIT)

    @exception_handler(PageHandlerError, logger, "Failed attempting to finish test")
    async def finish_road_code_test(self) -> None:
        """
        Find and click the 'Finish' button to complete the test.

        Note: The locator targets a 'span' element based on the original code.
        Verify if this is correct; often finish actions are buttons or links.
        Uses the reliable `_click_if_visible` helper.

        :raises PageHandlerElementNotFoundError: If the finish button cannot be found.
        :raises PageHandlerError: For other interaction errors.
        """
        logger.info("Attempting to click the 'Finish' button.")
        # Locate the finish element (span in this case)
        # Consider if 'button' or 'a' might be more appropriate depending on HTML.
        finish_locator = self.page.locator("span").filter(has_text="Finish")
        await self._click_if_visible(finish_locator, "Finish button")
        logger.info("Finish button clicked.")
        # Wait after finishing to allow the results page/summary to load
        await self.page.wait_for_timeout(self.DEFAULT_WAIT * 2)  # Longer wait potentially needed

    @exception_handler(PageHandlerError, logger, "Failed attempting to open answer accordion")
    async def open_answer_accordion(self) -> None:
        """
        Find and click the accordion toggle on the results page to reveal explanations.

        Uses the reliable `_click_if_visible` helper.

        :raises PageHandlerElementNotFoundError: If the accordion toggle cannot be found.
        :raises PageHandlerError: For other interaction errors.
        """
        logger.info("Attempting to click the answer explanation accordion.")
        # Locate the toggle element for the results accordion
        accordion_locator = self.page.locator("span.accordion__toggle")
        await self._click_if_visible(accordion_locator, "Answer accordion toggle")
        logger.info("Answer accordion toggle clicked.")
        # Wait after clicking the accordion to allow content to expand
        await self.page.wait_for_timeout(self.DEFAULT_WAIT)
