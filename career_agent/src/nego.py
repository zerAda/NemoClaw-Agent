import os
import logging
from typing import Dict, Optional
from .client_factory import ai_factory

logger = logging.getLogger(__name__)

class NegotiatorService:
    """Diamond-Grade Intelligent Salary Benchmarking & Negotiation support using Gemini."""
    
    def __init__(self, brain_path: str = ""):
        self.brain_path = brain_path
        self.client = ai_factory.get_client("gemini")
        # Fixed to 1.5 due to Free Tier API limits
        self.model_id = os.getenv("MODEL_ID", "gemini-1.5-flash")

    async def get_benchmarks(self, role: str, location: str = "France") -> str:
        """Returns specialized negotiation talking points synthesized by Gemini."""
        prompt = f"""
        Act as a top-tier Tech Executive Recruiter operating in {location}.
        I have just received an interview or offer for the role of: {role}.
        
        Please provide:
        1. A realistic market salary range (Base + Variable) for this role in {location} (Euro). 
        2. Three highly persuasive negotiation talking points I can use to justify asking for the top-quartile of this range.
        3. Strategic advice on perks to negotiate if the base salary is inflexible (e.g., RTT, Remote work, sign-on bonus).
        
        Keep your response highly structured, extremely professional, and formatted in markdown.
        """
        
        try:
            logger.info(f"Generating Negotiation Strategy for {role} in {location} via {self.model_id}")
            response = await self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": "You are a Diamond-Grade Career Negotiator specialized in the French market."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4
            )
            return response.choices[0].message.content or "Error generating benchmarks."
        except Exception as e:
            logger.error(f"NegotiatorService Gemini Error: {e}")
            return f"❌ Negotiation Strategy generation failed: {e}"
