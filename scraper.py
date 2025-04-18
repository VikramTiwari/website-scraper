from playwright.async_api import async_playwright
import json
from typing import Set, List, Dict, Any
from urllib.parse import urljoin, urlparse
import time
import asyncio
import os
import uuid
from datetime import datetime

# Load configuration
def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def load_websites():
    with open('websites.json', 'r') as f:
        return json.load(f)

config = load_config()
websites_config = load_websites()

async def scroll_to_bottom(page, max_scrolls: int = None, scroll_delay: float = None) -> None:
    """
    Scroll to the bottom of the page, waiting for content to load.

    Args:
        page: Playwright page object
        max_scrolls (int): Maximum number of scroll attempts
        scroll_delay (float): Delay between scrolls in seconds
    """
    max_scrolls = max_scrolls or config['scraper']['scroll']['max_scrolls']
    scroll_delay = scroll_delay or config['scraper']['scroll']['scroll_delay']
    
    last_height = await page.evaluate("document.body.scrollHeight")
    scroll_count = 0

    while scroll_count < max_scrolls:
        # Scroll to bottom
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(scroll_delay)  # Wait for content to load

        # Calculate new scroll height
        new_height = await page.evaluate("document.body.scrollHeight")

        # If height hasn't changed, we've reached the bottom
        if new_height == last_height:
            break

        last_height = new_height
        scroll_count += 1

async def _get_title_from_meta(page, meta_type: str) -> str:
    """Helper function to get title from meta tags"""
    try:
        if meta_type == "og":
            title = await page.locator('meta[property="og:title"]').get_attribute('content')
        elif meta_type == "twitter":
            title = await page.locator('meta[name="twitter:title"]').get_attribute('content')
        if title and title.strip():
            return title.strip()
    except Exception as e:
        print(f"Error getting {meta_type} title: {str(e)}")
    return None

async def get_page_title(page) -> str:
    """
    Get the page title with multiple fallback methods in parallel.
    
    Args:
        page: Playwright page object
        
    Returns:
        str: Page title or fallback text if title not found
    """
    # Try getting the title from the title tag first (most reliable)
    try:
        title = await page.title()
        if title and title.strip():
            return title.strip()
    except Exception as e:
        print(f"Error getting title: {e}")

    # Run all other fallbacks in parallel
    tasks = [
        page.locator('h1').first.text_content() if await page.locator('h1').count() > 0 else None,
        _get_title_from_meta(page, "og"),
        _get_title_from_meta(page, "twitter")
    ]
    
    # Get results as they complete
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result and result.strip():
                return result.strip()
        except Exception as e:
            print(f"Error in parallel title extraction: {e}")
    
    # If all else fails, return the URL
    return page.url

async def _get_description_from_meta(page, meta_type: str) -> str:
    """Helper function to get description from meta tags"""
    try:
        if meta_type == "standard":
            desc = await page.locator('meta[name="description"]').get_attribute('content')
        elif meta_type == "og":
            desc = await page.locator('meta[property="og:description"]').get_attribute('content')
        elif meta_type == "twitter":
            desc = await page.locator('meta[name="twitter:description"]').get_attribute('content')
        if desc and desc.strip():
            return desc.strip()
    except Exception as e:
        print(f"Error getting {meta_type} description: {str(e)}")
    return None

async def get_page_description(page) -> str:
    """
    Get the page description with multiple fallback methods in parallel.
    
    Args:
        page: Playwright page object
        
    Returns:
        str: Page description or None if no description found
    """
    # Run all description extraction methods in parallel
    tasks = [
        _get_description_from_meta(page, "standard"),
        _get_description_from_meta(page, "og"),
        _get_description_from_meta(page, "twitter"),
        page.locator('p').first.text_content() if await page.locator('p').count() > 0 else None
    ]
    
    # Get results as they complete
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result and result.strip():
                return result.strip()
        except Exception as e:
            print(f"Error in parallel description extraction: {e}")
    
    # Try getting from first meta tag with description in name as last resort
    try:
        meta_desc_tags = page.locator('meta[name*="description"]')
        count = await meta_desc_tags.count()
        for i in range(count):
            desc = await meta_desc_tags.nth(i).get_attribute('content')
            if desc and desc.strip():
                return desc.strip()
    except Exception as e:
        print(f"Error getting meta description tags: {str(e)}")
    
    return None

async def scrape_page(url: str, page) -> dict:
    """
    Scrape a single webpage and return its data.

    Args:
        url (str): URL to scrape
        page: Playwright page object

    Returns:
        dict: Page data
    """
    try:
        # Navigate to the page
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        
        # Wait for 2 seconds to ensure all dynamic content is loaded
        await asyncio.sleep(2)

        # Scroll to bottom to load all content
        await scroll_to_bottom(page)

        # Clean the page using page_functions.js
        try:
            with open('page_functions.js', 'r') as f:
                page_clean_script = f.read()
            await page.evaluate(page_clean_script)
            await page.evaluate("cleanPage()")
        except Exception as e:
            print(f"Error in page evaluation: {str(e)}")

        # Get page data
        data = {
            "url": page.url,
            "title": await get_page_title(page),
            "description": await get_page_description(page),
            "content": await page.content(),  # Get complete HTML content
            "links": set(),  # Use a set to store unique links
            "updated_at": datetime.utcnow().isoformat()  # Add UTC timestamp
        }

        # Get all links and convert relative URLs to absolute
        try:
            links = await page.locator("a").all()
            for a in links:
                try:
                    href = await a.get_attribute("href")
                    if href:
                        absolute_url = urljoin(url, href)
                        if absolute_url.startswith(("http://", "https://")):
                            data["links"].add(absolute_url)  # Add to set instead of list
                except Exception as e:
                    print(f"Error processing link: {str(e)}")
                    continue
        except Exception as e:
            print(f"Error getting links: {str(e)}")

        # Convert set to list and sort alphabetically
        data["links"] = sorted(list(data["links"]))

        # Save the scraped data to a file
        try:
            # Get domain for the current URL
            current_domain = urlparse(url).netloc
            
            # Create domain-specific directory
            domain_dir = os.path.join(config['output']['directory'], current_domain)
            os.makedirs(domain_dir, exist_ok=True)
            
            # Generate UUID for filename
            filename = f"{uuid.uuid4()}.json"
            filepath = os.path.join(domain_dir, filename)
            
            # Save the scraped data
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving data to file: {str(e)}")

        return data

    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

class AsyncPagePool:
    """Manages a pool of browser pages for async reuse"""
    def __init__(self, browser, pool_size=None):
        self.browser = browser
        self.pool_size = pool_size or config['scraper']['page_pool']['size']
        self.pages = []
        self.lock = asyncio.Lock()
        self.available = asyncio.Event()
        self.available.set()

    async def initialize(self):
        """Initialize the page pool"""
        for _ in range(self.pool_size):
            page = await self.browser.new_page()
            self.pages.append(page)

    async def get_page(self):
        """Get a page from the pool, creating a new one if pool is empty"""
        async with self.lock:
            if self.pages:
                return self.pages.pop()
            return await self.browser.new_page()

    async def return_page(self, page):
        """Return a page to the pool"""
        async with self.lock:
            if len(self.pages) < self.pool_size:
                self.pages.append(page)
            else:
                # Close the page if pool is full
                await page.close()

    async def cleanup(self):
        """Clean up all pages in the pool"""
        async with self.lock:
            for page in self.pages:
                await page.close()
            self.pages.clear()

async def scrape_site(start_url: str, max_pages: int = None, headless: bool = None) -> List[Dict]:
    """
    Recursively scrape a website starting from the given URL.

    Args:
        start_url (str): URL to start scraping from
        max_pages (int): Maximum number of pages to scrape
        headless (bool): Whether to run browser in headless mode

    Returns:
        List[Dict]: List of scraped page data
    """
    max_pages = max_pages or config['scraper']['max_pages']
    headless = headless if headless is not None else config['scraper']['headless']
    batch_size = config['scraper']['parallel_processing']['batch_size']

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        page_pool = AsyncPagePool(browser)
        await page_pool.initialize()

        try:
            visited_urls: Set[str] = set()
            urls_to_visit: Set[str] = {start_url}
            scraped_data: List[Dict] = []
            
            # Get the domain of the start URL
            start_domain = urlparse(start_url).netloc

            # Create outputs directory if it doesn't exist
            os.makedirs(config['output']['directory'], exist_ok=True)

            while urls_to_visit and len(scraped_data) < max_pages:
                # Get up to batch_size URLs to process in parallel
                current_batch = []
                while len(current_batch) < batch_size and urls_to_visit and len(scraped_data) + len(current_batch) < max_pages:
                    url = urls_to_visit.pop()
                    if url not in visited_urls:
                        current_batch.append(url)
                        visited_urls.add(url)

                if not current_batch:
                    break

                print(f"Scraping batch: {current_batch}")

                # Create tasks for parallel scraping
                tasks = []
                pages = []
                for url in current_batch:
                    page = await page_pool.get_page()
                    pages.append(page)
                    tasks.append(scrape_page(url, page))

                # Run tasks in parallel and collect results
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results and return pages to pool
                for i, (result, page) in enumerate(zip(results, pages)):
                    await page_pool.return_page(page)
                    
                    if isinstance(result, Exception):
                        print(f"Error in parallel scraping: {str(result)}")
                    elif result:
                        scraped_data.append(result)
                        # Add discovered links to urls_to_visit if they're from the same domain
                        for link in result.get('links', []):
                            link_domain = urlparse(link).netloc
                            if link_domain == start_domain and link not in visited_urls:
                                urls_to_visit.add(link)

            return scraped_data

        finally:
            await page_pool.cleanup()
            await browser.close()

def main():
    """Example usage of the scraper"""
    start_url = "https://vikramtiwari.com"
    data = asyncio.run(scrape_site(start_url))
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
