"""Standalone verification script for Phase 3 Wave 1.
Bypasses pytest setup to avoid MemoryError during hpack/respx loading.
"""
import os
import sys
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from career_agent.src.hunter import HunterService
from career_agent.src.models import JobListing, ScoreRecord

async def verify_hunter():
    print("--- Starting Expert Standalone Verification ---")
    
    # 1. Setup mock brain
    brain_path = "tmp_brain_test"
    os.makedirs(brain_path, exist_ok=True)
    with open(os.path.join(brain_path, "Bio_Context.md"), "w") as f:
        f.write("Test candidate bio.")
    with open(os.path.join(brain_path, "Target_Specs.json"), "w") as f:
        f.write('{"exclusions": ["intern"], "scoring_threshold": 0.85}')
    
    # 2. Test Fast-Fail
    print("Testing SCORE-02: Fast-fail logic...")
    hunter = HunterService(brain_path=brain_path)
    listing = JobListing(
        id="j1", title="Internship Position", source="linkedin", url="http://x.com"
    )
    
    record = await hunter.score_job(listing)
    assert record.fast_failed is True
    assert record.score == 0.0
    assert record.recommendation == "SKIP"
    assert "intern" in record.reasoning.lower()
    print("✓ Fast-fail verified.")
    
    # 3. Test Gemini Path (Mocked)
    print("Testing SCORE-01/03/04: Gemini scoring logic...")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "score": 0.9,
        "recommendation": "APPLY",
        "reasoning": "Strong match",
        "match_reasons": ["AI skills"],
        "gap_analysis": []
    })
    
    with patch("career_agent.src.hunter.ai_factory") as mock_factory:
        mock_factory.get_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
        
        hunter = HunterService(brain_path=brain_path)
        listing_ok = JobListing(id="j2", title="Senior AI Engineer", source="linkedin")
        record_ok = await hunter.score_job(listing_ok)
        
        assert record_ok.score == 0.9
        assert record_ok.threshold_met is True
        assert record_ok.recommendation == "APPLY"
        assert record_ok.fast_failed is False
        print("✓ Gemini scoring and threshold logic verified.")
        
    print("--- All Phase 3 Wave 1 logic verified successfully ---")

if __name__ == "__main__":
    asyncio.run(verify_hunter())
