from playwright.sync_api import sync_playwright
import json
from typing import Set, List, Dict, Any
from urllib.parse import urljoin, urlparse
import time
import concurrent.futures
from functools import partial

def scroll_to_bottom(page, max_scrolls: int = 10, scroll_delay: float = 1.0) -> None:
    """
    Scroll to the bottom of the page, waiting for content to load.

    Args:
        page: Playwright page object
        max_scrolls (int): Maximum number of scroll attempts
        scroll_delay (float): Delay between scrolls in seconds
    """
    last_height = page.evaluate("document.body.scrollHeight")
    scroll_count = 0

    while scroll_count < max_scrolls:
        # Scroll to bottom
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(scroll_delay)  # Wait for content to load

        # Calculate new scroll height
        new_height = page.evaluate("document.body.scrollHeight")

        # If height hasn't changed, we've reached the bottom
        if new_height == last_height:
            break

        last_height = new_height
        scroll_count += 1

def _get_title_from_meta(page, meta_type: str) -> str:
    """Helper function to get title from meta tags"""
    try:
        if meta_type == "og":
            title = page.locator('meta[property="og:title"]').get_attribute('content')
        elif meta_type == "twitter":
            title = page.locator('meta[name="twitter:title"]').get_attribute('content')
        if title and title.strip():
            return title.strip()
    except Exception as e:
        print(f"Error getting {meta_type} title: {str(e)}")
    return None

def get_page_title(page) -> str:
    """
    Get the page title with multiple fallback methods in parallel.
    
    Args:
        page: Playwright page object
        
    Returns:
        str: Page title or fallback text if title not found
    """
    # Try getting the title from the title tag first (most reliable)
    try:
        title = page.title()
        if title and title.strip():
            return title.strip()
    except Exception as e:
        print(f"Error getting title: {e}")

    # Run all other fallbacks in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Prepare all the title extraction functions
        futures = [
            executor.submit(lambda: page.locator('h1').first.text_content() if page.locator('h1').count() > 0 else None),
            executor.submit(partial(_get_title_from_meta, page, "og")),
            executor.submit(partial(_get_title_from_meta, page, "twitter"))
        ]
        
        # Get results as they complete
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result and result.strip():
                    return result.strip()
            except Exception as e:
                print(f"Error in parallel title extraction: {e}")
    
    # If all else fails, return the URL
    return page.url

def _get_description_from_meta(page, meta_type: str) -> str:
    """Helper function to get description from meta tags"""
    try:
        if meta_type == "standard":
            desc = page.locator('meta[name="description"]').get_attribute('content')
        elif meta_type == "og":
            desc = page.locator('meta[property="og:description"]').get_attribute('content')
        elif meta_type == "twitter":
            desc = page.locator('meta[name="twitter:description"]').get_attribute('content')
        if desc and desc.strip():
            return desc.strip()
    except Exception as e:
        print(f"Error getting {meta_type} description: {str(e)}")
    return None

def get_page_description(page) -> str:
    """
    Get the page description with multiple fallback methods in parallel.
    
    Args:
        page: Playwright page object
        
    Returns:
        str: Page description or None if no description found
    """
    # Run all description extraction methods in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Prepare all the description extraction functions
        futures = [
            executor.submit(partial(_get_description_from_meta, page, "standard")),
            executor.submit(partial(_get_description_from_meta, page, "og")),
            executor.submit(partial(_get_description_from_meta, page, "twitter")),
            executor.submit(lambda: page.locator('p').first.text_content() if page.locator('p').count() > 0 else None)
        ]
        
        # Get results as they complete
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result and result.strip():
                    return result.strip()
            except Exception as e:
                print(f"Error in parallel description extraction: {str(e)}")
    
    # Try getting from first meta tag with description in name as last resort
    try:
        meta_desc_tags = page.locator('meta[name*="description"]')
        for i in range(meta_desc_tags.count()):
            desc = meta_desc_tags.nth(i).get_attribute('content')
            if desc and desc.strip():
                return desc.strip()
    except Exception as e:
        print(f"Error getting meta description tags: {str(e)}")
    
    return None

def scrape_page(url: str, page) -> dict:
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
        page.goto(url)
        page.wait_for_load_state("networkidle")
        
        # Wait for 2 seconds to ensure all dynamic content is loaded
        time.sleep(2)

        # Scroll to bottom to load all content
        scroll_to_bottom(page)

        # Clean the page using page_functions.js
        try:
            with open('page_functions.js', 'r') as f:
                page_clean_script = f.read()
            page.evaluate(page_clean_script)
            page.evaluate("cleanPage()")
        except Exception as e:
            print(f"Error in page evaluation: {str(e)}")

        # Get page data
        data = {
            "url": page.url,
            "title": get_page_title(page),
            "description": get_page_description(page),
            "content": page.content(),  # Get complete HTML content
            "links": set()  # Use a set to store unique links
        }

        # Get all links and convert relative URLs to absolute
        try:
            for a in page.locator("a").all():
                try:
                    href = a.get_attribute("href")
                    if href:
                        absolute_url = urljoin(url, href)
                        if absolute_url.startswith(("http://", "https://")):
                            data["links"].add(absolute_url)  # Add to set instead of list
                except Exception as e:
                    print(f"Error processing link: {str(e)}")
                    continue
        except Exception as e:
            print(f"Error getting links: {str(e)}")

        # Convert set back to list for JSON serialization
        data["links"] = list(data["links"])
        return data

    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

def scrape_site(start_url: str, max_pages: int = 10, headless: bool = True) -> List[Dict]:
    """
    Recursively scrape a website starting from the given URL.

    Args:
        start_url (str): URL to start scraping from
        max_pages (int): Maximum number of pages to scrape
        headless (bool): Whether to run browser in headless mode

    Returns:
        List[Dict]: List of scraped page data
    """
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=headless)
    page = browser.new_page()

    try:
        visited_urls: Set[str] = set()
        urls_to_visit: Set[str] = {start_url}
        scraped_data: List[Dict] = []
        
        # Get the domain of the start URL
        start_domain = urlparse(start_url).netloc

        while urls_to_visit and len(scraped_data) < max_pages:
            # Get next URL to visit
            current_url = urls_to_visit.pop()

            # Skip if already visited
            if current_url in visited_urls:
                continue

            print(f"Scraping: {current_url}")

            # Scrape the page
            data = scrape_page(current_url, page)
            if data:
                scraped_data.append(data)
                visited_urls.add(current_url)

                # Add new links to visit only if they belong to the same domain
                for link in data["links"]:
                    link_domain = urlparse(link).netloc
                    if link_domain == start_domain and link not in visited_urls and link not in urls_to_visit:
                        urls_to_visit.add(link)

        return scraped_data

    finally:
        page.close()
        browser.close()
        playwright.stop()

def main():
    # Example usage
    start_url = "https://vikramtiwari.com"
    data = scrape_site(start_url, max_pages=50, headless=False)
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
