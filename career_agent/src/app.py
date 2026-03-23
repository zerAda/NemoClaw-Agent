import asyncio
import os
import logging
from typing import List

from .hunter import HunterService
from .tailor import TailorService
from .memory import MemoryService

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PhoenixApp")

class PhoenixApp:
    """The Orchestrator: Connecting all Career Agent modules."""

    def __init__(self, brain_path: str):
        self.brain_path = brain_path
        self.hunter = HunterService(brain_path=brain_path)
        self.tailor = TailorService(brain_path=brain_path)
        self.memory = MemoryService(brain_path=brain_path)

    async def process_job(self, job: Dict):
        """Standardized single-job processing atom with error isolation."""
        try:
            if self.memory.is_already_processed(job["url"]):
                logger.info(f"Skipping already seen job: {job['title']}")
                return

            # 1. Pull Full JD
            jd_text = await self.hunter.scraper.get_linkedin_job_description(job["url"])
            if not jd_text or len(jd_text) < 100:
                logger.warning(f"Invalid JD content for {job['title']}. Skipping.")
                return

            # 2. Score (Hunter)
            report = await self.hunter.score_job(jd_text)
            if report.recommendation == "SKIP":
                logger.info(f"SKIPPING: {job['title']} (Score: {report.score})")
                self.memory.add_application(job["url"], {"title": job["title"], "status": "SKIPPED", "score": report.score})
                return

            # 3. Tailor (If High Match)
            logger.info(f"MATCH FOUND: {job['title']}! Generating letter...")
            letter = await self.tailor.customize_letter(jd_text, report.dict())
            
            # 4. Save Artifacts using UUID for uniqueness
            job_id_uuid = self.memory._generate_uuid(job["url"])
            output_dir = os.path.join(self.brain_path, "applications", job_id_uuid)
            os.makedirs(output_dir, exist_ok=True)
            
            with open(os.path.join(output_dir, "cover_letter.txt"), "w") as f:
                f.write(letter.body)
            
            self.memory.add_application(job["url"], {
                "title": job["title"],
                "status": "READY",
                "score": report.score,
                "uuid": job_id_uuid
            })
            logger.info(f"ARTIFACT READY: {job['title']} -> {output_dir}")
        except Exception as e:
            logger.error(f"CRITICAL ERROR processing {job.get('title', 'Unknown')}: {e}")

    async def run_cycle(self, keyword: str, location: str = "United States"):
        """Run a high-performance parallel cycle."""
        logger.info(f"--- Starting PARALLEL Phoenix Cycle for: {keyword} ---")
        scraped_jobs = await self.hunter.scraper.search_linkedin_jobs(keyword, location)
        
        # Process up to 5 jobs concurrently
        tasks = [self.process_job(job) for job in scraped_jobs[:5]]
        await asyncio.gather(*tasks)
        logger.info("--- Parallel Cycle complete ---")

        logger.info("--- Cycle Complete ---")

async def main():
    # Ensure current directory is correct or use absolute path
    brain_path = "./brain"
    if not os.path.exists(brain_path):
        os.makedirs(brain_path)
        
    app = PhoenixApp(brain_path=brain_path)
    await app.run_cycle("AI Engineer")

if __name__ == "__main__":
    asyncio.run(main())
