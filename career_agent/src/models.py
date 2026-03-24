"""Unified data models for the career agent pipeline."""
from pydantic import BaseModel, Field
from typing import List, Optional

class JobListing(BaseModel):
    id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    date_posted: Optional[str] = None
    contract_type: Optional[str] = None
    source: str  # "france_travail" or "linkedin"
    raw: Optional[dict] = None

class MatchReport(BaseModel):
    """Gemini scoring output. reasoning is a single summary string; match_reasons is the supporting list."""
    score: float = Field(..., ge=0.0, le=1.0, description="Match percentage 0.0–1.0")
    recommendation: str = Field(..., description="APPLY, SKIP, or TAILOR_REQUIRED")
    reasoning: str = Field(..., description="Single-sentence summary of why this score was given")
    match_reasons: List[str] = Field(default_factory=list, description="Supporting reasons for the score")
    gap_analysis: List[str] = Field(default_factory=list, description="Missing skills or requirements")

class ScoreRecord(BaseModel):
    """Complete scoring outcome persisted to Qdrant per job. One record per JobListing."""
    job_id: str                          # JobListing.id
    title: str                           # JobListing.title
    company: Optional[str] = None        # JobListing.company
    source: str                          # JobListing.source ("france_travail" or "linkedin")
    url: Optional[str] = None            # JobListing.url
    score: float                         # 0.0 if fast-failed, else Gemini score
    recommendation: str                  # "APPLY", "SKIP", or "TAILOR_REQUIRED"
    reasoning: str                       # Gemini reasoning or fast-fail reason string
    fast_failed: bool = False            # True when exclusion keyword triggered (no Gemini call made)
    threshold_met: bool = False          # True when score >= scoring_threshold
