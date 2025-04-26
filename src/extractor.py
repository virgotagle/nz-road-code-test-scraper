# -*- coding: utf-8 -*-
"""
Module responsible for extracting structured data from NZ Road Code test web pages.

Uses Playwright Page objects to access page content and CSS selectors (from config)
or regular expressions to locate and parse relevant information like test URLs,
chapter details, questions, answers, and explanations.
"""

import json
import logging
import re  # Regular expression module
from contextlib import suppress  # Utility to ignore specific exceptions
from typing import List, Optional

from playwright.async_api import ElementHandle, Page

from .config import ROAD_CODE_BASE_URL, SelectorsConfig
from .exceptions import ExtractorError, exception_handler
from .image_downloader import ImageDownloader
from .schema import AnswerSchema, ChapterSchema, QuestionSchema

logger = logging.getLogger(__name__)


class Extractor:
    """
    Extracts structured data (Chapters, Questions, Answers) from Road Code test pages.

    Requires a Playwright Page object to interact with the DOM and an optional
    ImageDownloader to handle image fetching.
    """

    def __init__(self, page: Page, image_downloader: Optional[ImageDownloader] = None):
        """
        Initialize the Extractor.

        :param page: The active Playwright Page object representing the browser page.
        :type page: Page
        :param image_downloader: An instance for downloading images asynchronously.
                                 If None, a default instance is created.
        :type image_downloader: Optional[ImageDownloader]
        """
        self.page = page
        self.base_url = ROAD_CODE_BASE_URL
        self.selectors = SelectorsConfig()
        # Use provided downloader or create a default one
        self.image_downloader = image_downloader or ImageDownloader()
        logger.debug("Extractor initialized.")

    @exception_handler(ExtractorError, logger, "Failed to extract test URLs from landing page")
    async def get_all_road_code_tests_url(self) -> List[str]:
        """
        Find and return all URLs pointing to individual road code tests from the main landing page.

        Assumes the tests are linked within the last card of specific card lists.

        :return: A list of absolute URLs for the road code tests.
        :rtype: List[str]
        :raises ExtractorError: If the structure for finding URLs is not found or parsing fails.
        """
        urls = []
        # Locate all sections that might contain lists of chapters/tests
        card_lists = await self.page.query_selector_all("div.card__list")
        logger.debug(f"Found {len(card_lists)} potential card lists.")

        for card_list in card_lists:
            # Within each list, find all individual cards
            cards = await card_list.query_selector_all("div.card")
            if not cards:
                # Skip lists that don't contain cards
                continue

            # Assume the *last* card in the list links to the test for that section
            last_card = cards[-1]
            # Find the anchor tag (link) within the last card
            anchor = await last_card.query_selector("a")
            if anchor:
                href = await anchor.get_attribute("href")
                if href:
                    # Construct the absolute URL
                    full_url = f"{self.base_url}{href}"
                    urls.append(full_url)
                    logger.debug(f"Extracted test URL: {full_url}")

        if not urls:
            logger.warning("No test URLs were extracted. Check page structure and selectors.")
        else:
            logger.info(f"Successfully extracted {len(urls)} test URLs.")
        return urls

    @exception_handler(ExtractorError, logger, "Failed to extract chapter JSON from test page")
    async def get_test_chapter(self) -> ChapterSchema:
        """
        Extract chapter data (ID, title, intro, questions, answers) from the current page.

        Relies on finding a specific JavaScript variable (`window._rrltModuleContent`)
        embedded in the page's HTML containing the chapter data as JSON.

        :return: A ChapterSchema object populated with the extracted data.
        :rtype: ChapterSchema
        :raises ExtractorError: If the JavaScript variable or JSON data cannot be found or parsed.
        """
        logger.debug("Attempting to extract chapter JSON from page source.")
        content = await self.page.content()  # Get the full HTML source

        # Regular expression to find the JavaScript variable assignment and capture the JSON part.
        # `re.DOTALL` allows '.' to match newline characters.
        match = re.search(r"window\._rrltModuleContent\s*=\s*({.*?});", content, re.DOTALL)

        if not match:
            logger.error("Could not find 'window._rrltModuleContent' JSON data in page source.")
            raise ExtractorError("Chapter JSON data structure not found in page source.")

        try:
            # Extract the captured JSON string (group 1 of the match)
            json_string = match.group(1)
            # Parse the JSON string into a Python dictionary
            json_data = json.loads(json_string)
            logger.debug("Successfully parsed chapter JSON data.")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON data: {e}", exc_info=True)
            raise ExtractorError("Failed to parse chapter JSON data") from e
        except Exception as e:
            logger.error(f"Unexpected error processing chapter JSON: {e}", exc_info=True)
            raise ExtractorError("Unexpected error processing chapter JSON") from e

        # Transform the raw JSON data into the structured ChapterSchema
        questions = await self._transform_questions(json_data.get("Questions", []))
        chapter = ChapterSchema(
            id=json_data.get("ID"),
            title=json_data.get("Title"),
            intro=json_data.get("Intro"),
            questions=questions,
        )
        logger.info(f"Successfully extracted chapter '{chapter.title}' (ID: {chapter.id}).")
        return chapter

    async def _transform_questions(self, raw_questions: List[dict]) -> List[QuestionSchema]:
        """
        Convert a list of raw question dictionaries from JSON into QuestionSchema objects.

        :param raw_questions: List of dictionaries, each representing a question.
        :type raw_questions: List[dict]
        :return: A list of populated QuestionSchema objects.
        :rtype: List[QuestionSchema]
        """
        logger.debug(f"Transforming {len(raw_questions)} raw questions into schemas.")
        # Use list comprehension for concise transformation
        return [await self._build_question_schema(q) for q in raw_questions]

    async def _build_question_schema(self, q: dict) -> QuestionSchema:
        """
        Build a single QuestionSchema object from a raw question dictionary.

        Includes fetching and encoding the question image if available.

        :param q: A dictionary representing a single question's data.
        :type q: dict
        :return: A populated QuestionSchema object.
        :rtype: QuestionSchema
        """
        image_rel_path = q.get("Image")
        image_url = f"{self.base_url}{image_rel_path}" if image_rel_path else None
        image_base64 = None  # Initialize as None

        # If an image URL exists, attempt to download and encode it
        if image_url:
            logger.debug(f"Image URL found for question {q.get('ID')}: {image_url}")
            try:
                image_base64 = await self.image_downloader.download_to_base64(image_url)
                logger.debug(f"Successfully downloaded and encoded image for question {q.get('ID')}.")
            except Exception as e:
                # Log error but don't fail the whole extraction for one image
                logger.warning(f"Failed to download/encode image for question {q.get('ID')} from {image_url}: {e}")

        # Create the QuestionSchema instance
        return QuestionSchema(
            id=q.get("ID", ""),  # Use .get for safety, though ID should exist
            question=q.get("Question", ""),
            image_url=image_url,
            image_base64=image_base64,
            answers=self._build_answers(q.get("Answers", [])),  # Build nested answers
        )

    def _build_answers(self, raw_answers: List[dict]) -> List[AnswerSchema]:
        """
        Convert a list of raw answer dictionaries from JSON into AnswerSchema objects.

        Determines if an answer is correct based on the presence of the 'CorrectAnswer' key.

        :param raw_answers: List of dictionaries, each representing an answer.
        :type raw_answers: List[dict]
        :return: A list of populated AnswerSchema objects.
        :rtype: List[AnswerSchema]
        """
        answers = []
        for a in raw_answers:
            is_correct = a.get("CorrectAnswer") is not None  # Check presence of the key
            answers.append(
                AnswerSchema(
                    id=a.get("ID", ""),  # Use .get for safety
                    answer=a.get("Answer", ""),
                    is_correct_answer=is_correct,
                    # Explanation is added later after simulating the test
                )
            )
        return answers

    @exception_handler(ExtractorError, logger, "Failed to extract explanations from results carousel")
    async def get_correct_answers_explanations(self) -> List[str]:
        """
        Extract the explanation text for each question from the results carousel shown after test completion.

        Iterates through carousel cards and extracts text from specific elements
        assumed to contain the explanation.

        :return: A list of strings, where each string is the explanation for a question.
        :rtype: List[str]
        :raises ExtractorError: If carousel cards are not found or explanation extraction fails.
        """
        logger.debug("Attempting to extract explanations from results carousel.")
        explanations = []
        # Find all carousel cards using the configured selector
        cards = await self.page.query_selector_all(self.selectors.carousel_card)

        if not cards:
            logger.error("Could not find any carousel cards using selector: {self.selectors.carousel_card}")
            raise ExtractorError("Results carousel cards not found on the page.")

        logger.debug(f"Found {len(cards)} carousel cards.")
        # Process each card to extract its explanation
        for card in cards:
            # Extract potentially multiple parts of the explanation text from the card
            parts = await self._extract_explanation_from_card(card)
            # Join the parts into a single string for the explanation
            explanations.append("\n".join(p.strip() for p in parts if p))  # Join non-empty, stripped parts

        logger.info(f"Successfully extracted {len(explanations)} explanations from carousel.")
        return explanations

    async def _extract_explanation_from_card(self, card_element: ElementHandle) -> List[str]:
        """
        Extract text content from potential explanation elements within a single carousel card.

        Tries multiple selectors known to contain parts of the explanation text.

        :param card_element: The ElementHandle representing a single carousel card.
        :type card_element: ElementHandle
        :return: A list of text parts found within the card's explanation sections.
        :rtype: List[str]
        """
        explanation_parts = []
        # Define selectors likely to contain explanation text
        # Order might matter if text is duplicated; adjust as needed.
        explanation_selectors = [
            self.selectors.explanation_main,
            self.selectors.explanation_additional,
            # Add more specific selectors if needed, e.g., handling variations
            # Example: "div.carousel__content--tint > span > p:nth-child(2)", # A more specific selector if needed
        ]

        # Attempt to extract text using each defined selector
        for selector in explanation_selectors:
            # Use suppress(Exception) to gracefully handle cases where a selector doesn't find an element
            # or if inner_text() fails for some reason on an optional element.
            with suppress(Exception):  # Suppress errors like TimeoutError or if element detach
                text = await self._get_text_from_selector(card_element, selector)
                if text:
                    explanation_parts.append(text)
                # else:
                # Optionally log if a specific selector failed, can be noisy
                # logger.debug(f"No text found for selector '{selector}' in card.")

        return explanation_parts

    async def _get_text_from_selector(self, parent_element: ElementHandle, selector: str) -> Optional[str]:
        """
        Safely get the inner text content of an element matching the selector within a parent element.

        Returns None if the element is not found.

        :param parent_element: The ElementHandle within which to search.
        :type parent_element: ElementHandle
        :param selector: The CSS selector for the target child element.
        :type selector: str
        :return: The inner text of the found element, or None if not found.
        :rtype: Optional[str]
        """
        # Query for the child element within the parent
        child_element = await parent_element.query_selector(selector)
        # If the element exists, return its inner text
        if child_element:
            return await child_element.inner_text()
        # Return None if the element was not found
        return None
