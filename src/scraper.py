# -*- coding: utf-8 -*-
"""
Main scraper orchestration module.

Coordinates the process of scraping NZ Road Code test data using Browser,
PageHandler, Extractor, and DBHelper/ChapterService components. Manages the
overall workflow including navigation, data extraction, user simulation
(to get explanations), and database storage.
"""

import logging
from typing import List, Optional

from playwright.async_api import Page

from .browser import Browser
from .chapter_service import ChapterService
from .db_helper import DBHelper
from .exceptions import NZRoadCodeTestError, ScraperError, exception_handler
from .extractor import Extractor
from .page_handler import PageHandler
from .schema import ChapterSchema  # Use Pydantic schema for data transfer

logger = logging.getLogger(__name__)


class Scraper:
    """
    Orchestrates the scraping process for NZ Road Code tests.

    Manages browser interactions, data extraction, simulating test completion
    to obtain explanations, and storing the results in the database.
    Designed to be used as an asynchronous context manager.
    """

    def __init__(self, db_helper: Optional[DBHelper] = None, browser: Optional[Browser] = None) -> None:
        """
        Initialize the Scraper.

        :param db_helper: An instance of DBHelper for database interactions.
                          If None, a default instance is created.
        :type db_helper: Optional[DBHelper]
        :param browser: An instance of Browser for managing the Playwright browser.
                        If None, a default instance (headless Chromium) is created.
        :type browser: Optional[Browser]
        """
        # Use provided instances or create defaults
        self.browser = browser or Browser()
        self.db_helper = db_helper or DBHelper()
        # Ensure database schema is ready before scraping
        self.db_helper.initialize_schema()

        # Internal state for managing the async context
        self._page_context_manager = None
        self._page: Optional[Page] = None
        logger.debug("Scraper initialized.")

    async def __aenter__(self) -> "Scraper":
        """
        Enter the asynchronous context, initializing the browser page.

        Called when entering an `async with Scraper(...)` block.

        :return: The initialized Scraper instance.
        :rtype: Scraper
        :raises ScraperError: If initialization of the browser page fails.
        """
        logger.debug("Entering Scraper async context.")
        try:
            # Get the async context manager for the browser page
            self._page_context_manager = self.browser.page()
            # Enter the page context manager to get the actual Page object
            self._page = await self._page_context_manager.__aenter__()
            logger.info("Browser page obtained successfully.")
            return self  # Return the Scraper instance itself
        except Exception as e:
            # Catch any error during browser/page setup
            logger.exception("Failed to initialize browser page within Scraper context")
            # Wrap the error in a ScraperError
            raise ScraperError(f"Failed to initialize scraper context: {e}") from e

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the asynchronous context, cleaning up the browser page.

        Called when exiting the `async with` block, ensuring resources are released.

        :param exc_type: Exception type if an exception occurred within the context.
        :param exc_val: Exception value if an exception occurred.
        :param exc_tb: Traceback if an exception occurred.
        """
        logger.debug("Exiting Scraper async context.")
        if self._page_context_manager:
            try:
                # Exit the page context manager, triggering cleanup in Browser class
                await self._page_context_manager.__aexit__(exc_type, exc_val, exc_tb)
                logger.info("Browser page context exited successfully.")
            except Exception:
                logger.error("Error during Scraper context cleanup", exc_info=True)
                # Potentially re-raise or handle cleanup errors if needed
        self._page = None  # Reset internal state
        self._page_context_manager = None

    def _ensure_initialized(self) -> None:
        """
        Check if the scraper's page context has been successfully initialized.

        Internal helper method to be called before accessing `self._page`.

        :raises ScraperError: If the scraper is used outside of an `async with` block
                              or if initialization failed.
        """
        if self._page is None or self._page_context_manager is None:
            raise ScraperError(
                "Scraper not initialized or initialization failed. "
                "Ensure it's used within an 'async with Scraper()' block."
            )

    # --- Helper methods to get handlers/extractors ---
    # These ensure the page is initialized and provide easy access

    def _get_page_handler(self) -> PageHandler:
        """
        Get an initialized PageHandler instance.

        Ensures the scraper context is active before creating the handler.

        :return: An instance of PageHandler using the current page.
        :rtype: PageHandler
        """
        self._ensure_initialized()
        # Create a new PageHandler instance with the active page
        # Type ignore: self._page is guaranteed non-None by _ensure_initialized
        return PageHandler(self._page)  # type: ignore

    def _get_extractor(self) -> Extractor:
        """
        Get an initialized Extractor instance.

        Ensures the scraper context is active before creating the extractor.

        :return: An instance of Extractor using the current page.
        :rtype: Extractor
        """
        self._ensure_initialized()
        # Create a new Extractor instance with the active page
        # Type ignore: self._page is guaranteed non-None by _ensure_initialized
        return Extractor(self._page)  # type: ignore

    # --- Main Scraping Logic ---

    @exception_handler(ScraperError, logger, "Scraping process failed")
    async def scrape(self, test_urls: Optional[list[str]] = None) -> None:
        """
        Execute the full scraping process for NZ Road Code tests.

        Steps:
        1. Navigate to the main road code page.
        2. Extract all individual test chapter URLs (or use provided list).
        3. For each test URL:
            a. Navigate to the test page.
            b. Extract the chapter data (questions, answers).
            c. Simulate taking the test (clicking answers) to reach the results page.
            d. Extract explanations from the results page.
            e. Append explanations to the chapter data.
            f. Insert the complete chapter data into the database.

        :param test_urls: An optional list of specific test URLs to scrape.
                          If None, all tests found on the landing page are scraped.
        :type test_urls: Optional[list[str]]
        :raises ScraperError: If any critical step in the scraping workflow fails.
        """
        self._ensure_initialized()  # Ensure page is ready
        page_handler = self._get_page_handler()

        # 1. Navigate and get URLs
        await page_handler.goto_road_code_page()
        if test_urls is None:
            logger.info("No specific test URLs provided, extracting all from landing page.")
            test_urls = await self._get_all_test_urls()
        else:
            logger.info(f"Using provided list of {len(test_urls)} test URLs.")

        if not test_urls:
            logger.warning("No test URLs found or provided. Scraping cannot proceed.")
            return

        # 2. Process each URL
        # Use the DBHelper's session context manager for transaction control
        with self.db_helper.create_session() as session:
            # Create a service instance with the active session
            chapter_service = ChapterService(session)

            total_urls = len(test_urls)
            for index, url in enumerate(test_urls, 1):
                logger.info(f"--- Processing Test [{index}/{total_urls}]: {url} ---")
                try:
                    # 3a & 3b: Navigate and Extract Initial Chapter Data
                    chapter = await self._get_chapter_from_url(url)

                    # Basic validation before proceeding
                    if not chapter or not chapter.questions:
                        logger.warning(f"Skipping URL {url}: No valid chapter or questions extracted.")
                        continue  # Skip to the next URL

                    # Check if chapter already exists before simulation (optional optimization)
                    if chapter_service.chapter_exists(chapter.id):
                        logger.info(f"Chapter ID {chapter.id} ('{chapter.title}') already exists in DB. Skipping.")
                        continue

                    # 3c: Simulate Test Flow (Necessary to trigger explanation loading)
                    logger.info(f"Simulating test flow for chapter '{chapter.title}'...")
                    await self._simulate_user_test_flow(chapter)
                    logger.info("Test simulation complete.")

                    # 3d & 3e: Extract and Append Explanations
                    logger.info("Extracting and appending explanations...")
                    # It seems explanations require clicking the accordion *after* finishing
                    await page_handler.open_answer_accordion()  # Ensure explanations are visible
                    updated_chapter = await self._append_explanations(chapter)
                    logger.info("Explanations processed.")

                    # 3f: Insert into Database
                    logger.info(f"Attempting to insert chapter '{updated_chapter.title}' into database...")
                    inserted = chapter_service.insert_chapter(updated_chapter)
                    if inserted:
                        logger.info(f"Successfully prepared chapter '{updated_chapter.title}' for DB insertion.")
                    # Commit happens automatically when 'with db_helper.create_session()' block exits

                except NZRoadCodeTestError as e:
                    # Log specific errors encountered during processing of a single URL
                    logger.error(f"Failed to process URL {url}: {e}", exc_info=True)
                    # Continue to the next URL despite the error for this one
                    logger.warning(f"Continuing to next URL after error processing {url}.")
                    # Optionally, add a delay or other error handling here
                except Exception as e:
                    # Catch unexpected errors for a single URL
                    logger.exception(f"Unexpected error processing URL {url}: {e}")
                    logger.warning(f"Continuing to next URL after unexpected error processing {url}.")

        logger.info(f"--- Scraping finished. Processed {total_urls} URLs. ---")

    # --- Private Helper Methods for Scraping Steps ---

    # Apply exception handler to wrap potential errors in this specific step
    @exception_handler(ScraperError, logger, "Failed to get all test URLs")
    async def _get_all_test_urls(self) -> List[str]:
        """
        Extract all individual test chapter URLs from the main landing page.

        Requires clicking accordions first to reveal all links.

        :return: A list of absolute URLs for the tests.
        :rtype: List[str]
        """
        logger.debug("Getting all test URLs from landing page.")
        # Ensure accordions are open before extracting links
        await self._get_page_handler().click_road_code_test_accordions()
        # Use the extractor to get the URLs
        urls = await self._get_extractor().get_all_road_code_tests_url()
        if not urls:
            logger.warning("Extractor returned no test URLs from the landing page.")
        return urls

    # Apply exception handler
    @exception_handler(ScraperError, logger, "Failed to get chapter from URL")
    async def _get_chapter_from_url(self, url: str) -> Optional[ChapterSchema]:
        """
        Navigate to a specific test URL and extract the chapter data (questions, answers).

        Does *not* include explanations at this stage.

        :param url: The URL of the test chapter page.
        :type url: str
        :return: A ChapterSchema object, or None if extraction fails critically.
        :rtype: Optional[ChapterSchema]
        """
        logger.debug(f"Getting chapter data from URL: {url}")
        # Navigate to the specific test page
        await self._get_page_handler().goto_road_code_test(url)
        # Use the extractor to parse the chapter data from the page content
        chapter_data = await self._get_extractor().get_test_chapter()
        return chapter_data

    # Apply exception handler
    @exception_handler(ScraperError, logger, "Failed during user test flow simulation")
    async def _simulate_user_test_flow(self, chapter: ChapterSchema) -> None:
        """
        Simulate a user taking the test to reach the results/explanation page.

        Clicks the 'Start' button, then clicks an answer for each question
        (preferring an incorrect one if available), and clicks 'Next question'
        or 'Finish'.

        :param chapter: The ChapterSchema containing the questions and answers for the test.
        :type chapter: ChapterSchema
        """
        page_handler = self._get_page_handler()
        logger.debug(f"Starting test simulation for '{chapter.title}'.")
        await page_handler.start_road_code_test()

        num_questions = len(chapter.questions)
        for i, question in enumerate(chapter.questions):
            logger.debug(f"Simulating answer for question {i+1}/{num_questions} (ID: {question.id})")

            # Strategy: Click the first incorrect answer, or the first answer if all are correct (unlikely).
            # This ensures the 'explanation' section is typically shown for incorrect choices.
            wrong_answer = next((a.answer for a in question.answers if not a.is_correct_answer), None)
            answer_to_click = wrong_answer

            # Fallback: If somehow only correct answers are listed, or no answers, click the first one.
            if not answer_to_click and question.answers:
                answer_to_click = question.answers[0].answer
                logger.warning(f"Question {question.id} seems to have no incorrect answers? Clicking first answer.")

            # Click the chosen answer if one was determined
            if answer_to_click:
                await page_handler.click_answer(answer_to_click)
            else:
                # This case should ideally not happen if questions always have answers
                logger.error(
                    f"No answer found to click for question {question.id}. Cannot proceed with simulation accurately."
                )
                raise ScraperError(f"Cannot simulate test: No answer found for question ID {question.id}")

            # Navigate to the next question or finish the test
            if i < num_questions - 1:
                # If not the last question, click 'Next question'
                await page_handler.next_question()
            else:
                # If it is the last question, click 'Finish'
                logger.debug("Simulating final question, clicking Finish.")
                await page_handler.finish_road_code_test()

        logger.debug(f"Finished test simulation for '{chapter.title}'.")

    # Apply exception handler
    @exception_handler(ScraperError, logger, "Failed to append explanations")
    async def _append_explanations(self, chapter: ChapterSchema) -> ChapterSchema:
        """
        Extract explanations from the results page and add them to the correct answers in the ChapterSchema.

        Modifies a *copy* of the original chapter schema.

        :param chapter: The ChapterSchema object extracted earlier (without explanations).
        :type chapter: ChapterSchema
        :return: A new ChapterSchema instance with explanations added to the correct answers.
        :rtype: ChapterSchema
        """
        logger.debug("Extracting explanations from results page.")
        # Use the extractor to get the list of explanation strings from the carousel
        explanations = await self._get_extractor().get_correct_answers_explanations()

        # Important: Work on a deep copy to avoid modifying the original schema instance
        # if it's used elsewhere before this step completes.
        updated_chapter = chapter.model_copy(deep=True)

        num_questions = len(updated_chapter.questions)
        num_explanations = len(explanations)

        if num_questions != num_explanations:
            logger.warning(
                f"Mismatch between number of questions ({num_questions}) and "
                f"extracted explanations ({num_explanations}) for chapter '{updated_chapter.title}'. "
                f"Explanations might be incomplete or incorrect."
            )
            # Decide how to handle mismatch: proceed cautiously, raise error, etc.
            # Current approach: Process up to the minimum length.

        # Iterate through questions and explanations simultaneously
        for i, explanation in enumerate(explanations):
            # Protect against index errors if lists have different lengths
            if i < num_questions:
                question = updated_chapter.questions[i]
                # Find the correct answer within this question's answers
                correct_answer = next(
                    (ans for ans in question.answers if ans.is_correct_answer),
                    None,  # Default to None if no correct answer is found (shouldn't happen)
                )

                if correct_answer:
                    # Assign the extracted explanation to the correct answer
                    correct_answer.explanation = explanation
                    logger.debug(f"Appended explanation to correct answer for question {i+1} (QID: {question.id}).")
                else:
                    # Log a warning if a question doesn't seem to have a marked correct answer
                    logger.warning(
                        f"Could not find correct answer for question {i+1} "
                        f"(QID: {question.id}) in chapter '{updated_chapter.title}' to append explanation."
                    )
            else:
                # This case occurs if num_explanations > num_questions
                logger.warning(f"Found extra explanation at index {i}, but no corresponding question.")

        return updated_chapter  # Return the modified copy
