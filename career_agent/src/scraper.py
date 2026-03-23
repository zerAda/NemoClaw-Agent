import asyncio
import random
import logging
import yaml
import os
from playwright.async_api import async_playwright
try:
    from playwright_stealth import stealth_async
except ImportError:
    # playwright_stealth v2 renamed stealth_async → stealth
    from playwright_stealth import stealth as stealth_async

logger = logging.getLogger(__name__)

class Scraper:
    """Diamond Grade Stealth Scraper using externalized selectors."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._load_selectors()

    def _load_selectors(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "selectors.yaml")
        try:
            with open(config_path, "r") as f:
                self.selectors = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load selectors from {config_path}: {e}")
            self.selectors = {}

    async def search_linkedin_jobs(self, query: str, location: str = "United States"):
        """Search for LinkedIn jobs with advanced stealth navigation."""
        sel = self.selectors.get("linkedin", {})
        if not sel:
            logger.error("LinkedIn selectors missing from config!")
            return []

        search_url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={location}"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await stealth_async(page)
            
            logger.info(f"Searching LinkedIn: {query} in {location}...")
            await page.goto(search_url, wait_until="networkidle")
            await self._human_scroll(page)
            
            job_cards = await page.query_selector_all(sel.get("job_card", ".base-card"))
            logger.info(f"Found {len(job_cards)} candidate job cards.")
            
            scraped_jobs = []
            for card in job_cards[:5]:
                title_elem = await card.query_selector(sel.get("job_title", ".base-search-card__title"))
                url_elem = await card.query_selector(sel.get("job_url", "a"))
                
                if title_elem and url_elem:
                    scraped_jobs.append({
                        "title": (await title_elem.inner_text()).strip(),
                        "url": await url_elem.get_attribute("href"),
                        "source": "LinkedIn"
                    })
            
            await browser.close()
            return scraped_jobs

    async def get_linkedin_job_description(self, job_url: str) -> str:
        """Extract full JD text using external selectors."""
        sel = self.selectors.get("linkedin", {})
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            await stealth_async(page)
            
            await page.goto(job_url, wait_until="networkidle")
            await asyncio.sleep(2)
            
            jd_elem = await page.query_selector(sel.get("job_description", ".description__text"))
            text = (await jd_elem.inner_text()).strip() if jd_elem else ""
            await browser.close()
            return text

    async def _human_scroll(self, page):
        """Perform randomized human-like scrolling."""
        for _ in range(random.randint(2, 5)):
            await page.mouse.wheel(0, random.randint(300, 700))
            await asyncio.sleep(random.uniform(0.5, 1.5))
