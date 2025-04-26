# -*- coding: utf-8 -*-
"""
Live integration test for the scraper functionality.

This test performs a real scrape against a specific chapter URL on the
drive.govt.nz website, interacting with a live database. It verifies
that the scraper can successfully extract and store chapter data.

Note: Requires a live internet connection and the target website to be available.
Marked with 'live' to allow selective running via pytest markers.
"""

from typing import Optional

import pytest

# Assuming 'src' is accessible in the Python path for testing
from src.chapter_service import ChapterService
from src.db_helper import DBHelper
from src.model import Chapter
from src.scraper import Scraper


@pytest.mark.asyncio  # Mark the test function to be run with asyncio
@pytest.mark.live  # Custom marker for live tests
async def test_live_chapter_scraper():
    """
    Test scraping a single chapter and verifying its insertion into the database.

    Steps:
    1. Define a specific test chapter URL.
    2. Initialize the database schema.
    3. Run the scraper for the defined URL.
    4. Query the database to retrieve the scraped chapter.
    5. Assert that the retrieved data matches expected values.

    :raises AssertionError: If the retrieved data is not as expected.
    :raises pytest.fail: If the chapter is not found in the database after scraping.
    """
    # Specific URL for the "Rules and requirements" chapter test
    url = "https://drive.govt.nz/learner-licence/interactive-road-code/rules-and-requirements/test"

    # Set up the database helper and ensure schema exists
    db_helper = DBHelper()
    db_helper.initialize_schema()

    # Run the scraper within an async context manager
    # Use default browser settings (headless)
    async with Scraper() as scraper:
        # Scrape only the specified test URL
        await scraper.scrape(test_urls=[url])

    # Verify the data was inserted correctly
    with db_helper.create_session() as session:
        chapter_service = ChapterService(session)
        # Assuming the chapter ID can be reliably determined or is known.
        # Here, we try to retrieve based on a hypothetical ID (e.g., 2).
        # A more robust approach might involve querying by URL or title if IDs are dynamic.
        # For this example, we'll assume ID 2 corresponds to the scraped chapter.
        # TODO: Find a more reliable way to identify the scraped chapter if IDs aren't fixed.
        results: Optional[Chapter] = chapter_service.get_chapter(2)  # Example ID

        if results:
            # Check if the result is indeed a Chapter object
            assert isinstance(results, Chapter), "Expected a Chapter object"
            # Check if the title matches the expected chapter title
            # Type ignore used here as 'results' is confirmed not None inside this block.
            assert results.title == "Rules and requirements chapter test"  # type: ignore
        else:
            # Fail the test if no chapter was found with the given ID
            pytest.fail("No results found for chapter ID 2")
