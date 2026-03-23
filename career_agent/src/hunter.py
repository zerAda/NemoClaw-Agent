import os
import json
import logging
from typing import List, Dict
from pydantic import BaseModel, Field
from .scraper import Scraper
from .client_factory import ai_factory

logger = logging.getLogger(__name__)

class MatchReport(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0, description="Match percentage (0.0-1.0)")
    match_reasons: List[str] = Field(..., description="Key reasons for the score")
    gap_analysis: List[str] = Field(..., description="Missing skills or requirements")
    recommendation: str = Field(..., description="APPLY, SKIP, or TAILOR_REQUIRED")

class HunterService:
    """Diamond Grade Hunter: Scoring with Gemini & Centralized Clients."""
    
    def __init__(self, brain_path: str, headless: bool = True):
        self.brain_path = brain_path
        self.bio_context = self._load_bio()
        self.target_specs = self._load_specs()
        self.client = ai_factory.get_client("gemini")
        self.scraper = Scraper(headless=headless)

    def _load_bio(self) -> str:
        with open(os.path.join(self.brain_path, "Bio_Context.md"), "r") as f:
            return f.read()

    def _load_specs(self) -> Dict:
        with open(os.path.join(self.brain_path, "Target_Specs.json"), "r") as f:
            return json.load(f)

    def _fast_fail_check(self, jd_text: str) -> bool:
        exclusions = self.target_specs.get("exclusions", [])
        for word in exclusions:
            if word.lower() in jd_text.lower():
                logger.info(f"Fast-Fail: Found exclusion keyword '{word}'")
                return True
        return False

    async def score_job(self, jd_text: str) -> MatchReport:
        if not jd_text or len(jd_text) < 50:
            logger.warning("Empty or short JD received. Skipping LLM call.")
            return MatchReport(score=0.0, match_reasons=[], gap_analysis=["Incomplete JD"], recommendation="SKIP")

        if self._fast_fail_check(jd_text):
            return MatchReport(score=0.0, match_reasons=[], gap_analysis=["Fast-Fail exclusion"], recommendation="SKIP")

        prompt = f"""
        Analyze this Job Description against the Candidate's Bio.
        Candidate Bio: {self.bio_context}
        JD: {jd_text}
        Return JSON matching schema: {{score: float, match_reasons: list, gap_analysis: list, recommendation: string}}
        """
        
        logger.info("Generating Match Report via Gemini (Centralized Client)...")
        response = await self.client.chat.completions.create(
            model=os.getenv("MODEL_ID", "gemini-1.5-flash"),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.choices[0].message.content)
        return MatchReport(**data)
