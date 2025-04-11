# Simple Web Scraper with Playwright

A simple Python script for web scraping using Playwright that can recursively follow links.

## Features

- Headless browser automation
- Recursive scraping of linked pages
- URL tracking to prevent duplicate visits
- JSON output format with page data
- Simple and straightforward usage

## Installation

1. Clone this repository
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```
3. Install Playwright browsers:
```bash
playwright install
```

## Usage

The scraper can recursively scrape a website starting from a given URL:

```python
from scraper import scrape_site

# Scrape a website starting from the given URL
data = scrape_site("https://example.com", max_pages=10, headless=False)
print(data)  # This will print a list of JSON objects, each containing:
# [
#   {
#     "url": "https://example.com",
#     "title": "Example Domain",
#     "description": "Example meta description",
#     "content": "Page content...",
#     "links": ["https://example.com/link1", "https://example.com/link2"]
#   },
#   {
#     "url": "https://example.com/link1",
#     "title": "Linked Page",
#     ...
#   }
# ]
```

## Parameters

- `start_url`: The URL to start scraping from
- `max_pages`: Maximum number of pages to scrape (default: 10)
- `headless`: Whether to run the browser in headless mode (default: True)

## JSON Output Format

Each scraped page's data is in the following JSON format:

```json
{
  "url": "https://example.com",
  "title": "Page Title",
  "description": "Meta description of the page",
  "content": "Main content of the page",
  "links": [
    "https://example.com/link1",
    "https://example.com/link2"
  ]
}
```

## Example

The `main()` function in `scraper.py` provides a simple example of how to use the scraper. 