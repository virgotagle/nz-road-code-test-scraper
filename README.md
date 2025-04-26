
# NZ Road Code Test Scraper

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) <!-- Choose appropriate license -->

## Overview

This project is an asynchronous web scraper built with Python to extract road code test questions, answers, and associated images from the official NZTA *Drive* website (`https://drive.govt.nz/learner-licence/interactive-road-code`)[cite: 10]. The scraped data, including explanations and base64-encoded images, is then stored in a local SQLite database[cite: 10, 5, 9].

The primary goal is to demonstrate proficiency in various Python technologies relevant to web scraping, data processing, and application development.

## Features

* **Asynchronous Scraping:** Uses `asyncio` and `Playwright` for efficient, non-blocking browser automation and scraping[cite: 1, 12].
* **Data Extraction:** Parses HTML and embedded JSON to extract chapter details, questions, multiple-choice answers, and correct answer explanations[cite: 7].
* **Image Handling:** Downloads question images asynchronously (`aiohttp`) and encodes them to Base64 for storage directly within the database[cite: 6, 7].
* **Database Storage:** Uses `SQLAlchemy` ORM to interact with a SQLite database, storing the structured data persistently[cite: 4, 9, 11].
* **Data Validation:** Leverages `Pydantic` schemas to validate the structure and types of scraped data before processing and insertion[cite: 2, 11].
* **Modular Design:** Codebase is organized into logical components (browser control, page interaction, data extraction, database handling, configuration, etc.) for better maintainability[cite: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].
* **Configuration:** Centralized configuration for URLs, selectors, and network parameters[cite: 10].
* **Error Handling:** Implements custom exceptions and handlers for robust operation[cite: 8].
* **Logging:** Configurable logging to track the scraping process and diagnose issues[cite: 5].

## Tech Stack

* **Language:** Python 3.9+
* **Web Scraping/Automation:** Playwright[cite: 14]
* **Asynchronous HTTP:** aiohttp[cite: 14]
* **Database ORM:** SQLAlchemy[cite: 14]
* **Data Validation:** Pydantic[cite: 14]
* **Core Libraries:** asyncio

## Project Structure

```
nz_road_code_test_scraper/
├── assets/
│   ├── logs/                  # Log files are stored here [cite: 5]
│   └── road_code_test.db      # SQLite database file [cite: 10]
├── src/
│   ├── __init__.py
│   ├── browser.py             # Playwright browser management [cite: 12]
│   ├── chapter_service.py     # Handles DB operations for chapters [cite: 11]
│   ├── config.py              # Configuration constants and classes [cite: 10]
│   ├── db_helper.py           # SQLite database connection setup [cite: 9]
│   ├── exceptions.py          # Custom exception classes [cite: 8]
│   ├── extractor.py           # Data extraction logic from web pages [cite: 7]
│   ├── image_downloader.py    # Asynchronous image downloading [cite: 6]
│   ├── logging.py             # Logging setup [cite: 5]
│   ├── model.py               # SQLAlchemy ORM models [cite: 4]
│   ├── page_handler.py        # Playwright page interactions [cite: 3]
│   ├── schema.py              # Pydantic data schemas [cite: 2]
│   └── scraper.py             # Main scraping orchestration logic [cite: 1]
├── test/
│   └── test_live_scraper.py   # Example integration/live test [cite: 13]
├── main.py                    # Entry point to run the scraper [cite: 15]
├── requirements.txt           # Project dependencies [cite: 14]
└── README.md                  # This file
```

## Getting Started

### Prerequisites

* Python 3.9 or higher
* pip (Python package installer)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd nz_road_code_test_scraper
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    # On Windows
    python -m venv venv
    .\venv\Scripts\activate

    # On macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright browsers:**
    This command downloads the necessary browser binaries (Chromium by default).
    ```bash
    playwright install
    ```

## Usage

To run the scraper and populate the `assets/road_code_test.db` database[cite: 15]:

```bash
python main.py
```

By default, the scraper runs in headless mode (browser window is not visible). To run with the browser window visible for debugging[cite: 15]:

```bash
python main.py --headless false
```

The scraper will:
1.  Initialize the database schema if `assets/road_code_test.db` doesn't exist[cite: 9].
2.  Navigate to the main Road Code test page[cite: 3].
3.  Discover all individual chapter test URLs[cite: 7].
4.  For each test URL:
    * Extract chapter metadata, questions, and answers[cite: 7].
    * Download and encode associated images[cite: 6].
    * Simulate taking the test to reveal answer explanations[cite: 1, 3].
    * Extract explanations[cite: 7].
    * Store the complete chapter data in the database[cite: 1, 11].
5.  Log progress and potential errors to the console and `assets/logs/`[cite: 5].

## Configuration

* **Database:** The SQLite database is stored at `assets/road_code_test.db`[cite: 10].
* **Logs:** Log files are generated in the `assets/logs/` directory[cite: 5].
* **Target URLs & Selectors:** Core URLs and CSS selectors used for scraping are defined in `src/config.py`[cite: 10].

## Ethical Considerations

* This scraper is intended for educational purposes and demonstrating technical skills.
* Scraping websites can place load on their servers. This script includes default timeouts and implicit waits but run it responsibly.
* Be mindful of the terms of service of the target website (`https://drive.govt.nz/learner-licence/interactive-road-code`).
* The scraped data is publicly available information from the *Drive* website.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an Issue. (Optional: Add more specific contribution guidelines if desired).

## License

This project is licensed under the MIT License - see the LICENSE file for details. (Optional: Create a `LICENSE` file with the MIT license text).


