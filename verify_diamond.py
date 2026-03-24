"""Standalone verification script for Diamond-Grade Round 5 logic.
Bypasses pytest setup to avoid MemoryError during hpack/respx loading on this machine.
"""
import os
import sys
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from career_agent.src.hunter import HunterService
from career_agent.src.tailor import TailorService, TailoredContent
from career_agent.src.memory import MemoryService
from career_agent.src.models import JobListing, ScoreRecord

async def verify_diamond_grade():
    print("--- Starting Diamond-Grade Standalone Verification ---")
    
    # 1. Setup mock brain
    brain_path = "tmp_diamond_brain"
    os.makedirs(brain_path, exist_ok=True)
    with open(os.path.join(brain_path, "Bio_Context.md"), "w", encoding="utf-8") as f:
        f.write("Test candidate bio.")
    with open(os.path.join(brain_path, "Target_Specs.json"), "w", encoding="utf-8") as f:
        f.write('{"exclusions": ["intern"], "scoring_threshold": 0.85}')
    
    # 2. Test MemoryService (DI and O(1) retrieve)
    print("Testing MemoryService DI...")
    memory = MemoryService(brain_path=brain_path)
    url = "https://example.com/job/1"
    memory.add_application(url, {"title": "Test Job", "status": "SCORED"})
    assert memory.is_already_processed(url) is True
    print("✓ MemoryService DI and Retrieval verified.")
    
    # 3. Test HunterService (DI)
    print("Testing HunterService DI...")
    hunter = HunterService(brain_path=brain_path)
    listing = JobListing(id="j1", title="Internship", source="linkedin", url=url)
    record = await hunter.score_job(listing)
    assert record.fast_failed is True
    print("✓ HunterService fast-fail with DI verified.")
    
    # 4. Test TailorService (DI and ScoreRecord passing)
    print("Testing TailorService DI...")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "subject": "Tailored Sub",
        "body": "Tailored Body",
        "suggested_edits": []
    })
    
    with patch("career_agent.src.tailor.ai_factory") as mock_factory:
        mock_factory.get_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
        
        tailor = TailorService(brain_path=brain_path)
        score_rec = ScoreRecord(
            job_id="j1", title="AI Eng", source="linkedin", url=url,
            score=0.9, recommendation="APPLY", reasoning="Good match", threshold_met=True
        )
        content = await tailor.customize_letter("Mock JD", score_rec)
        assert content.subject == "Tailored Sub"
        print("✓ TailorService with ScoreRecord DI verified.")

    print("--- All Diamond-Grade Round 5 logic verified successfully ---")

if __name__ == "__main__":
    asyncio.run(verify_diamond_grade())
