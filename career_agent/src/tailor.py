import os
import json
import logging
from typing import Dict, List
from pydantic import BaseModel, Field
from .client_factory import ai_factory

logger = logging.getLogger(__name__)

class TailoredContent(BaseModel):
    subject: str = Field(..., description="Subject line")
    body: str = Field(..., description="Main body")
    suggested_edits: List[str] = Field(..., description="Recommended manual tweaks")

class TailorService:
    """Diamond Grade Tailor: Professional writing with centralized Gemini Pro."""

    def __init__(self, brain_path: str):
        self.brain_path = brain_path
        self.client = ai_factory.get_client("gemini")

    async def customize_letter(self, jd_text: str, match_report: Dict) -> TailoredContent:
        prompt = f"""
        Write a professional cover letter.
        JD: {jd_text}
        Score Analysis: {json.dumps(match_report)}
        Return JSON with 'subject', 'body', 'suggested_edits'.
        """
        
        logger.info("Generating tailored letter via Gemini Pro (Centralized Client)...")
        response = await self.client.chat.completions.create(
            model=os.getenv("MODEL_ID", "gemini-1.5-flash"),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.choices[0].message.content)
        return TailoredContent(**data)
