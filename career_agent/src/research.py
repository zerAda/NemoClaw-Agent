import os
import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

from .client_factory import ai_factory
from .logger import get_logger

class InterviewBriefing(BaseModel):
    company_snapshot: str = Field(description="Summary of the company and recent news")
    the_why_you: str = Field(description="How the candidate's bio aligns with the role")
    trap_questions: List[str] = Field(description="3 hard interview questions they might ask")
    your_turn: List[str] = Field(description="2 strategic questions to ask the interviewer")

class ResearchService:
    """Diamond-Grade autonomous web research using DDG and Gemini."""
    
    def __init__(self, brain_path: str = ""):
        self.brain_path = brain_path or os.environ.get("BRAIN_PATH", "/app/brain")
        self.client = ai_factory.get_client("gemini")
        self.logger = get_logger(__name__, "SYSTEM")
        self.model_id = os.getenv("MODEL_ID", "gemini-1.5-flash")
        
        # Load bio
        self.bio_context = self._load_bio()

    def _load_bio(self) -> str:
        path = os.path.join(self.brain_path, "Bio_Context.md")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.logger.warning(f"Bio_Context.md not found for Research: {e}")
            return "No background info available."

    async def search_company(self, company_name: str) -> str:
        """Use DDG to scrape recent information about the company."""
        if DDGS is None:
            self.logger.error("duckduckgo_search not installed.")
            return "Web search API unavailable."
            
        self.logger.info(f"Researching company: {company_name}")
        search_results = []
        try:
            # We use an explicit DDGS context to ensure proper closure
            with DDGS() as ddgs:
                results = ddgs.text(
                    keywords=f"{company_name} company overview recent news culture tech stack",
                    region='wt-wt',
                    safesearch='off',
                    max_results=5
                )
                for r in results:
                    search_results.append(f"Title: {r.get('title')}\nSnippet: {r.get('body')}\n")
        except Exception as e:
            self.logger.error(f"DDG Search failed for {company_name}: {e}")
            return "Web search failed. Rely on LLM internal knowledge."
            
        return "\n".join(search_results)

    async def generate_briefing(self, company_name: str, job_title: str, job_description: str = "") -> InterviewBriefing:
        """Synthesize web research, local bio, and job definition into a briefing."""
        
        web_context = await self.search_company(company_name)
        
        prompt = f"""
        EXPERT TASK: Generate a Diamond-Grade Interview Briefing.
        
        <target_company>
        {company_name}
        </target_company>
        
        <target_role>
        {job_title}
        </target_role>
        
        <candidate_bio>
        {self.bio_context}
        </candidate_bio>
        
        <web_research>
        {web_context}
        </web_research>
        
        <job_description>
        {job_description or "Job description not provided, rely on standard assumptions for role."}
        </job_description>
        
        CONSTRAINTS:
        1. Parse the web_research to understand the company's domain, recent activities, or culture.
        2. Give a quick 'Company Snapshot'.
        3. Frame the candidate's bio explicitly to match the role and company culture ('The Why You').
        4. Give 3 hard/technical behavioral 'trap' questions tailored to this role ('trap_questions').
        5. Give 2 highly strategic questions the candidate should ask to impress the interviewer ('your_turn').
        6. Return ONLY a valid JSON object matching the requested schema keys: 'company_snapshot', 'the_why_you', 'trap_questions', 'your_turn'.
        7. Language: Output in the dominant language of the job description or candidate bio (typically English or French).
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            self.logger.info(f"Generated interview briefing for {company_name}")
            return InterviewBriefing(**data)
        except Exception as e:
            self.logger.error(f"Failed to generate briefing: {e}")
            return InterviewBriefing(
                company_snapshot=f"Could not generate snapshot: {e}",
                the_why_you="Execution error.",
                trap_questions=["Error generating questions"],
                your_turn=["Error generating questions"]
            )
