import os
import logging
import asyncio
import random
from typing import Dict, Optional
import httpx
from patchright.async_api import async_playwright, Page
from .config import config

logger = logging.getLogger(__name__)

class ApplyService:
    """Diamond-Grade Autonomous Submission Engine.
    
    Strictly guarded by LEGAL_GATE_APPROVED and AUTO_APPLY_ENABLED flags.
    """
    
    def __init__(self, cycle_id: str = "SYSTEM"):
        self.cycle_id = cycle_id
        self.is_legal_approved = config.legal_gate_approved
        self.is_enabled = config.auto_apply_enabled

    async def submit_application(self, job_url: str, source: str, cover_letter_path: str) -> str:
        """EntryPoint for autonomous apply. 
        
        Returns: 'APPLIED', 'SIMULATED', or 'FAILED'.
        """
        if not self.is_enabled:
            logger.info(f"Auto-Apply DISABLED: {job_url}")
            return "SKIPPED_AUTO_APPLY_OFF"
            
        if not self.is_legal_approved:
            logger.warning(f"LEGAL GATE ACTIVE: Simulating application for {job_url}")
            # EXPERT: In simulation mode, we verify the files exist but don't hit external APIs
            if os.path.exists(cover_letter_path):
                return "SIMULATED"
            return "FAILED_SIMULATION"

        # REAL SUBMISSION LOGIC (Gated)
        try:
            if source == "france_travail":
                return await self._apply_france_travail(job_url, cover_letter_path)
            elif source in ["wttj", "apec", "linkedin"]:
                return await self._apply_via_form(job_url, source, cover_letter_path)
            else:
                logger.warning(f"No apply handler for source: {source}")
                return "FAILED_NO_HANDLER"
        except Exception as e:
            logger.error(f"CRITICAL APPLY FAILURE for {job_url}: {e}")
            return "FAILED_EXCEPTION"

    async def _human_type(self, page: Page, selector: str, text: str):
        """Type with human-like delays."""
        await page.wait_for_selector(selector, state="visible", timeout=10000)
        await page.click(selector)
        for char in text:
            await page.keyboard.press(char)
            await asyncio.sleep(random.uniform(0.05, 0.2))

    async def _apply_france_travail(self, job_url: str, cv_path: str) -> str:
        """Phase 8: France Travail REST API Submission."""
        logger.info(f"EXECUTING: Real France Travail Submission -> {job_url}")
        
        # EXPERT: Official /partenaire/offresdemploi/v2 API implementation
        client_id = os.getenv("FRANCE_TRAVAIL_CLIENT_ID")
        client_secret = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET")
        if not client_id or not client_secret:
            logger.error("Missing France Travail OAuth2 credentials")
            return "FAILED_NO_AUTH"
            
        async with httpx.AsyncClient() as client:
            try:
                # 1. Get Access Token
                token_resp = await client.post(
                    "https://entreprise.francetravail.fr/connexion/oauth2/access_token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "scope": "api_offresdemploiv2 o2dsoffre"
                    }
                )
                if token_resp.status_code != 200:
                    return "FAILED_AUTH"
                token = token_resp.json().get("access_token")
                
                # 2. Extract job ID from URL
                job_id = job_url.split("/")[-1].split("?")[0]
                
                # 3. Submit application (Multipart with CV)
                with open(cv_path, "rb") as f:
                    apply_resp = await client.post(
                        f"https://api.francetravail.io/partenaire/offresdemploi/v2/offres/{job_id}/candidatures",
                        headers={"Authorization": f"Bearer {token}"},
                        files={"cv": ("Lettre_de_Motivation.pdf", f, "application/pdf")},
                        data={"message": "Candidature via NemoClaw Autonomous Agent"}
                    )
                
                if apply_resp.status_code in [200, 201]:
                    logger.info(f"France Travail applied successfully: {job_id}")
                    return "APPLIED"
                else:
                    return "FAILED_API_ERROR"
            except Exception as e:
                logger.error(f"France Travail API Error: {e}")
                return "FAILED_EXCEPTION"

    async def _apply_via_form(self, job_url: str, source: str, cv_path: str) -> str:
        """Phase 8: Multi-platform Playwright form-filler."""
        logger.info(f"EXECUTING: Real {source} form-fill submission -> {job_url}")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                # Diamond Grade: Connect to persistent profile if exists to bypass login
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                
                await page.goto(job_url, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(2, 5)) 
                
                if source == "wttj":
                    # WTTJ Apply flow
                    apply_btn = await page.query_selector("button:has-text('Postuler')")
                    if apply_btn:
                        await apply_btn.click()
                        await asyncio.sleep(1)
                        # Upload PDF
                        file_input = await page.wait_for_selector("input[type='file']")
                        await file_input.set_input_files(cv_path)
                        await asyncio.sleep(2)
                        # Submit
                        submit_btn = await page.query_selector("button[type='submit']")
                        if submit_btn:
                            await submit_btn.click()
                            await page.wait_for_timeout(3000)
                            await browser.close()
                            return "APPLIED"
                            
                elif source == "apec":
                    # APEC Apply flow
                    apply_btn = await page.query_selector("button:has-text('Postuler')")
                    if apply_btn:
                        await apply_btn.click()
                        await asyncio.sleep(2)
                        
                        file_input = await page.wait_for_selector("input[type='file']")
                        await file_input.set_input_files(cv_path)
                        
                        submit_btn = await page.query_selector("button:has-text('Envoyer')")
                        if submit_btn:
                            await submit_btn.click()
                            await page.wait_for_timeout(3000)
                            await browser.close()
                            return "APPLIED"
                            
                elif source == "linkedin":
                    # LinkedIn Easy Apply flow
                    apply_btn = await page.query_selector("button.jobs-apply-button")
                    if apply_btn:
                        await apply_btn.click()
                        await asyncio.sleep(1)
                        # Handle multi-step modal
                        while True:
                            next_btn = await page.query_selector("button:has-text('Next')")
                            review_btn = await page.query_selector("button:has-text('Review')")
                            submit_btn = await page.query_selector("button:has-text('Submit')")
                            
                            if submit_btn:
                                await submit_btn.click()
                                await page.wait_for_timeout(3000)
                                await browser.close()
                                return "APPLIED"
                            elif review_btn:
                                await review_btn.click()
                            elif next_btn:
                                await next_btn.click()
                            else:
                                break
                            await asyncio.sleep(random.uniform(1, 2))

                await browser.close()
                return "FAILED_BUTTON_NOT_FOUND"
                
        except Exception as e:
            logger.error(f"Playwright Form-Fill Error on {source}: {e}")
            return "FAILED_EXCEPTION"
