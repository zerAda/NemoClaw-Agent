import os
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ProjectConfig:
    """Diamond Grade Configuration Singleton."""
    
    _instance = None
    
    def __new__(cls, brain_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(ProjectConfig, cls).__new__(cls)
            cls._instance._initialized = False
            # Diamond Grade: Initialize attributes to safe defaults to avoid AttributeError
            cls._instance.brain_path = None
            cls._instance.bio_context = ""
            self._instance.target_specs = {}
            self._instance.model_id = os.getenv("MODEL_ID", "gemini-1.5-flash")
            # Phase 8: Hard Legal Gates for Autonomous Submission
            self._instance.legal_gate_approved = os.getenv("LEGAL_GATE_APPROVED", "false").lower() == "true"
            self._instance.auto_apply_enabled = os.getenv("AUTO_APPLY_ENABLED", "false").lower() == "true"
            
        if brain_path:
            cls._instance.initialize(brain_path)
        return cls._instance

    def initialize(self, brain_path: str):
        if getattr(self, "_initialized", False) and self.brain_path == brain_path:
            return
            
        self.brain_path = brain_path
        self._load_bio()
        self._load_specs()
        self.model_id = os.getenv("MODEL_ID", "gemini-1.5-flash")
        self._initialized = True
        logger.info(f"ProjectConfig initialized with brain_path: {brain_path}")

    def _load_bio(self) -> None:
        path = os.path.join(self.brain_path, "Bio_Context.md")
        try:
            with open(path, "r") as f:
                self.bio_context = f.read()
        except Exception as e:
            logger.debug(f"Bio not loaded from {path}: {e}")
            self.bio_context = ""

    def _load_specs(self) -> None:
        path = os.path.join(self.brain_path, "Target_Specs.json")
        try:
            with open(path, "r") as f:
                self.target_specs = json.load(f)
        except Exception as e:
            logger.debug(f"Specs not loaded from {path}: {e}")
            self.target_specs = {}

# Global access point
config = ProjectConfig()
