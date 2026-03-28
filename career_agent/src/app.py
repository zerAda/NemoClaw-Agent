import asyncio
import os
from typing import List

from .hunter import HunterService
from .tailor import TailorService
from .memory import MemoryService
from .alerter import AlertService
from .scraper import Scraper
from .models import JobListing, ScoreRecord
from .tracking import TrackingService
from .document import PDFService
from .apply import ApplyService
from .config import config
from .logger import configure_logging, get_logger

# Initialize root logging
configure_logging()

class PhoenixApp:
    """Expert Orchestrator: Diamond-Grade Resilience and Observability."""

    def __init__(self, brain_path: str, cycle_id: str = "SYSTEM"):
        # EXPERT: Initialize global config once for legacy support, but prefer DI below
        config.initialize(brain_path)
        
        self.cycle_id = cycle_id
        self.brain_path = brain_path
        self.logger = get_logger("PhoenixApp", cycle_id)
        
        # Professional Throttling: Prevents VPS memory exhaustion and bot detection
        self.semaphore = asyncio.Semaphore(2)
        
        # EXPERT: All services now injected with brain_path
        self.alerter = AlertService()
        self.memory = MemoryService(brain_path=brain_path)
        self.tracking = TrackingService(brain_path=brain_path)
        self.document = PDFService()
        self.apply = ApplyService(cycle_id=cycle_id)
        self.scraper = Scraper(brain_path=brain_path, alerter=self.alerter, cycle_id=cycle_id)
        self.hunter = HunterService(brain_path=brain_path, cycle_id=cycle_id)
        self.tailor = TailorService(brain_path=brain_path, cycle_id=cycle_id)

    async def process_job(self, job: JobListing):
        """Standardized single-job processing with timeouts and detailed state tracking."""
        try:
            # Diamond Grade: Implement strict timeout to prevent hung cycles
            await asyncio.wait_for(self._process_job_task(job), timeout=120.0)
        except asyncio.TimeoutError:
            self.logger.error(f"ABANDONED: Processing TIMEOUT (120s) for '{job.title}'")
            self.memory.add_application(job.url, {
                "title": job.title, "status": "ABANDONED", "reasoning": "Processing timeout"
            })
        except Exception as e:
            self.logger.error(f"Orchestrator Failure [{job.title}]: {type(e).__name__}: {e}")

    async def _process_job_task(self, job: JobListing):
        """Internal task logic with Semaphore access and Diamond-Grade Error Handling."""
        async with self.semaphore:
            try:
                self.logger.info(f"Processing: {job.title} ({job.source})")
                
                # Phase 5: Relational Fingerprint Check
                fingerprint = self.tracking.generate_fingerprint(job.title, job.company)
                is_dupe = await self.tracking.is_duplicate(fingerprint)
                
                if is_dupe or self.memory.is_already_processed(job.url):
                    self.logger.info(f"Skipping Duplicate (Fingerprint: {fingerprint[:8]}): {job.title}")
                    return

                # 1. Pull Full JD (Retries)
                jd_text = ""
                for attempt in range(max(1, int(os.getenv("SCRAPE_RETRIES", 2)))):
                    jd_text = await self.scraper.get_job_description(job.url, job.source)
                    if jd_text: break
                    self.logger.warning(f"Retry JD extraction ({attempt+1}) for {job.title} [{job.source}]")
                    await asyncio.sleep(2)

                # --- Observability: Log JD Extraction failures specifically ---
                if not jd_text or len(jd_text) < 100:
                    self.logger.error(f"ABANDONED: {job.title} - JD Extraction Failed or Insufficient.")
                    await self.tracking.upsert_application(job.id, fingerprint, "ABANDONED", job.__dict__)
                    self.memory.add_application(job.url, {
                        "title": job.title, "source": job.source, "status": "ABANDONED", 
                        "reasoning": "Failed to extract readable job description"
                    })
                    return

                # 2. Score (AI Alignment)
                score_record = await self.hunter.score_job(jd_text, job.url)
                
                if score_record.recommendation == "SKIP":
                    self.logger.info(f"SKIP ({score_record.score}): {job.title} - {score_record.reasoning}")
                    await self.tracking.upsert_application(job.id, fingerprint, "SKIPPED", job.__dict__, score=score_record.score)
                    return

                # 3. Tailor (Bio-Aware Generation)
                self.logger.info(f"DIAMOND MATCH ({score_record.score}): {job.title}. Tailoring...")
                # EXPERT: Pass full score_record object for intelligence sharing
                letter = await self.tailor.customize_letter(jd_text, score_record)
                
                # 4. Persistence
                job_id = self.memory._generate_uuid(job.url)
                out_path = os.path.join(self.brain_path, "applications", job_id)
                os.makedirs(out_path, exist_ok=True)
                
                # Using shortened cycle_id for filename readability
                with open(os.path.join(out_path, f"cover_letter_{self.cycle_id[:8]}.txt"), "w", encoding="utf-8") as f:
                    f.write(letter.body)
                
                self.memory.add_application(job.url, {
                    "title": job.title, "status": "READY", "score": score_record.score,
                    "recommendation": score_record.recommendation,
                    "reasoning": score_record.reasoning,
                    "cycle_id": self.cycle_id, "uuid": job_id
                })
                
                # Phase 7: Professional PDF Generation
                pdf_path = os.path.join(out_path, f"Lettre_de_Motivation_{job_id[:8]}.pdf")
                self.document.create_cover_letter(letter.subject, letter.body, pdf_path)
                
                # Phase 8: Autonomous Apply Service (Gated)
                apply_status = await self.apply.submit_application(job.url, job.source, pdf_path)
                
                # Phase 5: Finalize state in relational tracker
                await self.tracking.upsert_application(job_id, fingerprint, apply_status, job.__dict__, score=score_record.score)
                
                self.logger.info(f"SUCCESS ({apply_status}): {job.title} -> {out_path}")
            except Exception as e:
                self.logger.error(f"CRITICAL ERROR processing {job.title}: {e}", exc_info=True)
                # Ensure we don't spam alerts for every single job failure, but log it.

    async def run_cycle(self, keyword: str, location: str = "France"):
        """Run standard search and process cycle with Diamond-Grade lifecycle management."""
        await self.alerter.send_info(f"🚀 Starting Cycle: {keyword} @ {location}")
        self.logger.info(f"=== Starting Cycle: {keyword} @ {location} ===")

        # Managed scraper context ensures browser cleanup even on failure
        async with self.scraper as managed_scraper:
            results = await asyncio.gather(
                managed_scraper.search_france_travail_jobs(keyword),
                managed_scraper.search_linkedin_jobs(keyword, location),
                managed_scraper.search_wttj_jobs(keyword, location),
                managed_scraper.search_apec_jobs(keyword, location),
                return_exceptions=True,
            )

            all_jobs: List[JobListing] = []
            for result in results:
                if isinstance(result, list): all_jobs.extend(result)
                elif isinstance(result, Exception): self.logger.error(f"Search Failure: {result}")

            self.logger.info(f"Initial Pool: {len(all_jobs)} jobs.")

            # Batch process up to 15 jobs (throttled by semaphore)
            tasks = [self.process_job(job) for job in all_jobs[:15]]
            await asyncio.gather(*tasks)

        self.logger.info(f"=== Cycle Finished [{self.cycle_id}] ===")
        await self.alerter.send_info(f"✅ Cycle Finished [{self.cycle_id[:8]}]: Processed {len(all_jobs[:15])} jobs.")
