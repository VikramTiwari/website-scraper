import json
import asyncio
import argparse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from scraper import scrape_site

def load_websites():
    """Load website configurations from websites.json"""
    with open('websites.json', 'r') as f:
        return json.load(f)

def load_config():
    """Load general configuration from config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)

async def create_scrape_job(site_config, general_config):
    """Create a scraping job for a specific website"""
    async def scrape_job():
        print(f"Starting scrape for {site_config['name']}")
        try:
            data = await scrape_site(
                site_config['url'],
                max_pages=site_config.get('max_pages', general_config['scraper']['max_pages'])
            )
            print(f"Completed scraping {site_config['name']}")
        except Exception as e:
            print(f"Error in scraping {site_config['name']}: {str(e)}")
    return scrape_job

async def run_immediate_scrape(website_name: str = None):
    """Run scraping jobs immediately for specified website or all enabled websites"""
    websites_config = load_websites()
    general_config = load_config()
    
    if website_name:
        # Find the specific website
        website = next((w for w in websites_config['websites'] 
                       if w['name'].lower() == website_name.lower() and w['enabled']), None)
        if not website:
            print(f"Website '{website_name}' not found or not enabled")
            return
        websites = [website]
    else:
        # Get all enabled websites
        websites = [w for w in websites_config['websites'] if w['enabled']]
    
    if not websites:
        print("No enabled websites found")
        return
    
    # Run scraping jobs
    for website in websites:
        job = await create_scrape_job(website, general_config)
        await job()

async def schedule_scraping():
    """Schedule scraping jobs for all enabled websites"""
    websites_config = load_websites()
    general_config = load_config()
    scheduler = AsyncIOScheduler()
    
    for website in websites_config['websites']:
        if website['enabled']:
            # Create and schedule the job
            job = await create_scrape_job(website, general_config)
            scheduler.add_job(
                job,
                CronTrigger.from_crontab(website['schedule']),
                id=f"scrape_{website['name'].lower().replace(' ', '_')}",
                name=f"Scrape {website['name']}"
            )
    
    # Start the scheduler
    scheduler.start()
    print("Scheduler started")
    
    try:
        # Keep the script running
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

def main():
    """Main entry point for the scheduler"""
    parser = argparse.ArgumentParser(description='Website Scraper Scheduler')
    parser.add_argument('--run-once', action='store_true', help='Run scraping jobs once and exit')
    parser.add_argument('--website', type=str, help='Specific website to scrape (by name)')
    args = parser.parse_args()
    
    if args.run_once:
        asyncio.run(run_immediate_scrape(args.website))
    else:
        asyncio.run(schedule_scraping())

if __name__ == "__main__":
    main() 