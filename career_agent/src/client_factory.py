import os
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

class ClientFactory:
    """Diamond Grade Centralized factory for AI clients with resilience."""
    
    _instance = None
    _clients = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ClientFactory, cls).__new__(cls)
        return cls._instance

    def get_client(self, provider: str = "gemini") -> AsyncOpenAI:
        """Get or initialize an AI client with retry logic."""
        if provider not in self._clients:
            logger.info(f"Initializing {provider} client with Diamond-Grade resilience...")
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment!")
            
            # OpenAI client (standard AI provider interface)
            self._clients[provider] = AsyncOpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                max_retries=3,  # Hardened resilience
                timeout=60.0    # Professional timeout
            )
        return self._clients[provider]

# Global access point
ai_factory = ClientFactory()
