import os
import logging
import json
from typing import Dict, Optional
from .client_factory import ai_factory
from .logger import get_logger

logger = logging.getLogger(__name__)

class FollowUpService:
    """Expert Re-engagement Engine.
    
    Proactively drafts professional follow-up messages for applied jobs.
    """
    
    def __init__(self, brain_path: str, cycle_id: str = "SYSTEM"):
        self.client = ai_factory.get_client("gemini")
        self.logger = get_logger(__name__, cycle_id)
        self.model_id = os.getenv("MODEL_ID", "gemini-1.5-flash")
        self.brain_path = brain_path

    async def draft_followup(self, app_record: Dict) -> Dict:
        """Draft a polite, high-impact follow-up via Gemini."""
        prompt = f"""
        EXPERT WRITER TASK: Professional Job Application Follow-Up (Relance).
        
        <job_context>
        Title: {app_record.get('title')}
        Company: {app_record.get('company')}
        Original URL: {app_record.get('url')}
        Applied Date: {app_record.get('timestamp')}
        </job_context>
        
        CONSTRAINTS:
        1. LANGUAGE: Strict French (FR-fr).
        2. TONE: Formal 'Vouvoiement' (Vous). Short, professional, and enthusiastic.
        3. PURPOSE: Re-iterate interest and ask if additional info is needed.
        4. STRUCTURE: 1-2 concise paragraphs.
        5. JSON KEYS: 'subject', 'body'.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            self.logger.error(f"Follow-Up Drafting Fail: {e}")
            return {
                "subject": f"Relance : {app_record.get('title')}",
                "body": f"Bonjour, je me permets de vous relancer concernant ma candidature pour le poste de {app_record.get('title')}. Cordialement."
            }
