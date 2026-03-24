import asyncio
import random
import logging
import yaml
import os
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self

import httpx
from patchright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page
from .models import JobListing
from .alerter import AlertService
from .logger import get_logger

# Pool of high reputation User Agents for rotation
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edge/121.0.0.0"
]

class FTConfig:
    """France Travail API Configuration."""
    TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
    SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
    DEFAULT_COUNT = 50
    MAX_RANGE = 149

class Scraper:
    """Elite Stealth Scraper: Expert-grade anti-bot evasion and session management."""
    
    def __init__(self, headless: bool = True, brain_path: str = "", alerter: Optional[AlertService] = None, cycle_id: str = "SYSTEM"):
        self.headless = headless
        self.brain_path = brain_path
        self.alerter = alerter or AlertService()
        self.logger = get_logger(__name__, cycle_id)
        self.selectors: Dict[str, Any] = {}
        self._rate_limits: Dict[str, Any] = {}
        
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        
        self._load_selectors()
        self._rate_limits = self._load_rate_limits()

    async def __aenter__(self) -> Self:
        """Initialize browser with Elite-Grade stealth profile."""
        if not self._playwright:
            self._playwright = await async_playwright().start()
            
            # EXPERT: Harden launch args for anti-bot evasion
            selected_ua = random.choice(UA_POOL)
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-position=0,0",
                "--ignore-certifcate-errors",
                "--ignore-certifcate-errors-spki-list",
                f"--user-agent={selected_ua}"
            ]
            
            self._browser = await self._playwright.chromium.launch(
                channel="chrome",
                headless=self.headless,
                args=launch_args,
                # EXPERT: Specifically exclude automation flags
                handle_sigint=True,
                handle_sigterm=True,
                handle_sighup=True
            )
            
            # EXPERT: Realistic context settings
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=selected_ua,
                locale="fr-FR",
                timezone_id="Europe/Paris",
                java_script_enabled=True,
                bypass_csp=True
            )
            
            # EXPERT: Add specialized stealth headers
            await self._context.set_extra_http_headers({
                "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
                "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Upgrade-Insecure-Requests": "1"
            })
            
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._playwright = None
        self._context = None

    def _load_selectors(self) -> None:
        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "selectors.yaml")
        try:
            with open(config_path, "r") as f:
                self.selectors = yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load selectors from {config_path}: {e}")
            self.selectors = {}

    def _load_rate_limits(self) -> dict:
        defaults = {"france_travail_daily": 50, "linkedin_daily": 15, "min_delay_s": 2, "max_delay_s": 5}
        if not self.brain_path: return defaults
        specs_path = os.path.join(self.brain_path, "Target_Specs.json")
        try:
            with open(specs_path) as f:
                specs = json.load(f)
            return specs.get("rate_limits", defaults)
        except Exception as e:
            self.logger.warning(f"Could not load rate limits from {specs_path}: {e}")
            return defaults

    async def _human_delay(self) -> None:
        delay = random.uniform(self._rate_limits.get("min_delay_s", 2), self._rate_limits.get("max_delay_s", 5))
        await asyncio.sleep(delay)

    async def _get_france_travail_token(self) -> str:
        client_id = os.getenv("FRANCE_TRAVAIL_CLIENT_ID")
        client_secret = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise ValueError("FRANCE_TRAVAIL_CLIENT_ID and FRANCE_TRAVAIL_CLIENT_SECRET must be set")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                FTConfig.TOKEN_URL,
                data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret, "scope": "api_offresdemploiv2 o2dsoffre"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            return resp.json()["access_token"]

    async def search_france_travail_jobs(self, keywords: str, count: int = FTConfig.DEFAULT_COUNT) -> List[JobListing]:
        try:
            token = await self._get_france_travail_token()
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    FTConfig.SEARCH_URL,
                    params={"motsCles": keywords, "range": f"0-{min(count, FTConfig.MAX_RANGE) - 1}"},
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
                resp.raise_for_status()
                resultats = resp.json().get("resultats", [])
                jobs = [self._parse_ft_listing(r) for r in resultats]
                if not jobs:
                    await self.alerter.send_alert("France Travail", "0 results")
                return jobs
        except Exception as e:
            self.logger.error(f"France Travail API failure: {type(e).__name__}")
            await self.alerter.send_alert("France Travail", type(e).__name__)
            return []

    def _parse_ft_listing(self, raw: dict) -> JobListing:
        return JobListing(
            id=raw.get("id", ""),
            title=raw.get("intitule", ""),
            company=raw.get("entreprise", {}).get("nom"),
            location=raw.get("lieuTravail", {}).get("libelle"),
            description=raw.get("description"),
            url=raw.get("origineOffre", {}).get("urlOrigine"),
            date_posted=raw.get("dateCreation"),
            contract_type=raw.get("typeContrat"),
            source="france_travail",
            raw=raw,
        )

    async def search_linkedin_jobs(self, query: str, location: str = "France") -> List[JobListing]:
        sel = self.selectors.get("linkedin", {})
        if not sel: return []
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={location}"
        
        if self._context:
            return await self._scrape_linkedin_with_context(self._context, search_url, sel, query, location)
        
        async with self as managed:
            return await self._scrape_linkedin_with_context(managed._context, search_url, sel, query, location)

    async def _scrape_linkedin_with_context(self, context: BrowserContext, url: str, sel: Dict, query: str, location: str) -> List[JobListing]:
        page = await context.new_page()
        try:
            self.logger.info(f"Stealth Search: LinkedIn {query} in {location}")
            await page.goto(url, wait_until="networkidle")
            await self._human_scroll(page)
            
            job_cards = await page.query_selector_all(sel.get("job_card", ".base-card"))
            scraped_jobs = []
            
            for card in job_cards[:min(len(job_cards), 15)]:
                title_elem = await card.query_selector(sel.get("job_title", ".base-search-card__title"))
                url_elem = await card.query_selector(sel.get("job_url", "a"))
                
                if title_elem and url_elem:
                    job_url = await url_elem.get_attribute("href")
                    title_text = (await title_elem.inner_text()).strip()
                    scraped_jobs.append(JobListing(id=job_url or f"li-{random.getrandbits(32)}", title=title_text, url=job_url, source="linkedin"))
            
            return scraped_jobs
        except Exception as e:
            self.logger.error(f"LinkedIn Search Fail: {type(e).__name__}")
            return []
        finally:
            await page.close()

    async def get_linkedin_job_description(self, job_url: str) -> str:
        sel = self.selectors.get("linkedin", {})
        if self._context:
            return await self._extract_jd_with_context(self._context, job_url, sel)
        async with self as managed:
            return await self._extract_jd_with_context(managed._context, job_url, sel)

    async def _extract_jd_with_context(self, context: BrowserContext, url: str, sel: Dict) -> str:
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            # EXPERT: Add jitter/waiting before extraction
            await asyncio.sleep(random.uniform(1.5, 3.0))
            jd_elem = await page.query_selector(sel.get("job_description", ".description__text"))
            return (await jd_elem.inner_text()).strip() if jd_elem else ""
        except Exception as e:
            self.logger.error(f"JD Extraction Fail: {type(e).__name__}")
            return ""
        finally:
            await page.close()

    async def _human_scroll(self, page: Page) -> None:
        for _ in range(random.randint(2, 4)):
            await page.mouse.wheel(0, random.randint(400, 800))
            await asyncio.sleep(random.uniform(0.6, 1.2))
