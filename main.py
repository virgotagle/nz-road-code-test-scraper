# -*- coding: utf-8 -*-
"""
Main entry point for the NZ Road Code Test Scraper application.

This script parses command-line arguments, ensures necessary directories and
database schema exist, initializes the scraping components, and runs the
main scraping process asynchronously.
"""

import argparse
import asyncio
import os  # Added for directory creation
import pathlib  # Added for path manipulation
from typing import Optional

# Note: src imports assume the script is run from the project root
# or the 'src' directory is in the Python path.
from src.browser import Browser  # Corrected import name
from src.config import ROAD_CODE_TEST_DB_URL  # Added for DB path
from src.db_helper import DBHelper  # Added for schema initialization
from src.logging import setup_logging  # Added for logging setup
from src.scraper import Scraper


def parse_args():
    """
    Parse command-line arguments for the scraper.

    Currently supports controlling the browser's headless mode.

    :return: Parsed command-line arguments.
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="NZ Road Code Test Scraper - A Playwright-based automation to extract road code test questions."
    )
    parser.add_argument(
        "--headless",
        action="store_false",  # Action is 'store_false' so the flag makes it False
        default=True,  # Default is headless
        help="Run browser in non-headless mode (shows browser window)",
    )
    return parser.parse_args()


async def main():
    """
    Asynchronous main function to set up and run the scraper.

    Ensures assets directory and database schema exist, initializes the
    browser (if needed) and the main Scraper class, then executes the scraping process.
    """
    args = parse_args()

    # --- Setup Logging ---
    # Determine log directory path relative to this script or project root
    # Assuming main.py is in the project root
    log_dir = pathlib.Path("assets/logs")
    setup_logging(log_dir=str(log_dir))  # Initialize logging first

    # --- Ensure Assets Directory Exists ---
    # Extract the directory path from the DB URL using rsplit for robustness
    # Example: "sqlite:///assets/road_code_test.db" -> "assets/road_code_test.db"
    # Use rsplit starting from the right, max 1 split, take the last part.
    db_file_path_str = ROAD_CODE_TEST_DB_URL.rsplit("///", maxsplit=1)[-1]
    db_path = pathlib.Path(db_file_path_str)
    asset_dir = db_path.parent  # Get the parent directory (e.g., 'assets')
    try:
        os.makedirs(asset_dir, exist_ok=True)
        print(f"Ensured asset directory exists: {asset_dir}")
    except OSError as e:
        print(f"Error creating asset directory {asset_dir}: {e}")
        return  # Exit if we can't create the directory

    # --- Initialize Database Schema ---
    try:
        db_helper = DBHelper()  # Uses default URL from config
        db_helper.initialize_schema()  # Create DB file and tables if they don't exist
        print("Database schema initialized successfully.")
    except Exception as e:
        print(f"Error initializing database schema: {e}")
        return  # Exit if DB setup fails

    # --- Initialize Browser (Optional) ---
    browser: Optional[Browser] = None  # Initialize browser as None
    if not args.headless:
        browser = Browser(headless=args.headless)

    # --- Run Scraper ---
    # Pass the already initialized db_helper instance
    # The scraper no longer needs to initialize the schema itself
    async with Scraper(db_helper=db_helper, browser=browser) as scraper:
        await scraper.scrape()


# Standard Python idiom to check if the script is executed directly.
if __name__ == "__main__":
    # Run the asynchronous main function using asyncio's event loop.
    asyncio.run(main())
