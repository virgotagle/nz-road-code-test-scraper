# -*- coding: utf-8 -*-
"""
Configuration module for the NZ Road Code Test Scraper.

Defines constants, enumerations, and dataclasses used throughout the application
to manage settings like URLs, selectors, network parameters, and browser types.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum

# === Constants ===
# Base URL for the target website
ROAD_CODE_BASE_URL: str = "https://drive.govt.nz"
# URL for the main page listing road code tests
ROAD_CODE_TEST_URL: str = f"{ROAD_CODE_BASE_URL}/learner-licence/interactive-road-code"
# Database connection URL (using SQLite in the assets directory)
ROAD_CODE_TEST_DB_URL: str = "sqlite:///assets/road_code_test.db"

# Default User-Agent string to mimic a common browser
DEFAULT_USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/100.0.4896.127 Safari/537.36"
)


# === Enums ===
class BrowserType(str, Enum):
    """Enumeration for supported Playwright browser types."""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


# === Config Classes ===
# Using dataclasses for structured configuration objects


@dataclass
class NetworkConfig:
    """Holds network-related configuration options."""

    timeout: float = 30.0  # Request timeout in seconds
    max_retries: int = 3  # Maximum number of retries for failed requests
    retry_delay: float = 1.0  # Delay between retries in seconds
    verify_ssl: bool = True  # Whether to verify SSL certificates


@dataclass
class SelectorsConfig:
    """
    Stores CSS selectors used by the Extractor to find elements on web pages.

    Keeping selectors centralized here makes them easier to update if the
    website structure changes.
    """

    # Selector for the element showing total question count in a test
    question_count: str = 'span[class="progress__question"]'
    # Selector for the main title of a test chapter
    title: str = 'h2[class="module__title"]'
    # Selector for the question text when there is no associated image
    question_no_image: str = 'div[class="question__question question__question--noimage"]'
    # Selector for the question text when there is an associated image
    question_with_image: str = 'div[class="question__question"]'
    # Selector for the image associated with a question
    question_image: str = 'img[class="question__image"]'
    # Selector for the container holding the answer choices
    answers_container: str = 'div[class="blocklist"]'
    # Selector for an individual answer item within the container
    answer_item: str = 'div[class="blocklist"] > div'
    # Selector for cards in the results carousel (containing explanations)
    carousel_card: str = 'div[class="carousel__card"]'
    # Selector for the question number within a carousel card
    question_number: str = 'p[class="carousel__questionNumber"]'
    # Selector for the text indicating the correct answer within a carousel card
    correct_answer: str = 'div[class="carousel__point"] > p'
    # Selector for the main explanation paragraph within a carousel card
    explanation_main: str = 'div[class="carousel__content carousel__content--tint"] > p'
    # Selector for additional explanation text (often in a span) within a carousel card
    explanation_additional: str = 'div[class="carousel__content carousel__content--tint"] > span > p'


@dataclass
class ExtractorConfig:
    """Main configuration container potentially for the Extractor (currently lightly used)."""

    base_url: str = ROAD_CODE_BASE_URL
    network: NetworkConfig = field(default_factory=NetworkConfig)  # Nested config
    selectors: SelectorsConfig = field(default_factory=SelectorsConfig)  # Nested config
    log_level: int = logging.INFO  # Example: Could be used to set specific log levels
