# Website Scraper

A Python-based website scraper that can be run either as a one-time job or on a schedule using cron expressions.

## Features

- Scrapes websites recursively up to a specified depth
- Extracts page titles, descriptions, and content
- Sorts links alphabetically
- Can run on a schedule using cron expressions
- Supports parallel processing
- Configurable through JSON files

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

### General Configuration (config.json)

```json
{
    "scraper": {
        "max_pages": 50,
        "headless": false,
        "scroll": {
            "max_scrolls": 10,
            "scroll_delay": 1.0
        },
        "page_pool": {
            "size": 5
        },
        "parallel_processing": {
            "batch_size": 3
        }
    },
    "output": {
        "directory": "outputs"
    }
}
```

### Website Configuration (websites.json)

```json
{
    "websites": [
        {
            "url": "https://example.com",
            "name": "Example Site",
            "schedule": "0 */6 * * *",
            "max_pages": 100,
            "enabled": true
        }
    ]
}
```

## Usage

### Running the Scraper Directly

To scrape a single website:

```bash
python scraper.py
```

### Using the Scheduler

1. Run all enabled websites on their schedules:
```bash
python scheduler.py
```

2. Run all enabled websites once and exit:
```bash
python scheduler.py --run-once
```

3. Run a specific website once:
```bash
python scheduler.py --run-once --website "Example Site"
```

### Cron Schedule Format

The schedule uses standard cron format:
- `0 */6 * * *` - Every 6 hours
- `0 0 * * *` - Once daily at midnight
- `0 0 * * 0` - Once weekly on Sunday
- `0 0 1 * *` - Once monthly on the 1st

## Output

Scraped data is saved in the configured output directory (`outputs` by default) with the following structure:
```
outputs/
  └── domain.com/
      └── [uuid].json
```

Each JSON file contains:
- URL
- Title
- Description
- Content
- Sorted list of links
- Timestamp

## Error Handling

- Failed scrapes are logged with error messages
- The scheduler continues running even if individual scrapes fail
- One-time runs exit after completion or error 