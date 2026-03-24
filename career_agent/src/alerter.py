import os
import logging
from typing import Optional

try:
    from telegram import Bot
except ImportError:
    Bot = None  # Fallback for environments where package is missing

logger = logging.getLogger(__name__)

class AlertService:
    """Diamond Grade Alerting: Telegram-based notification gateway."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("NEMO_AUTH_USER_ID")
        
        if not self.token or not self.chat_id:
            logger.warning("AlertService: Missing credentials. Alerts will be logged but not sent.")

    async def send_alert(self, platform: str, message: str) -> bool:
        """Send an urgent alert to the user. Swallows exceptions to prevent cycle death."""
        if not self.token or not self.chat_id or Bot is None:
            logger.info(f"[OFFLINE ALERT] {platform}: {message}")
            return False

        try:
            bot = Bot(token=self.token)
            full_msg = f"‼️ {platform} Scraper Alert\n\nIssue: {message}\nSeverity: HIGH"
            
            logger.info(f"Sending Telegram alert for {platform}...")
            await bot.send_message(chat_id=self.chat_id, text=full_msg)
            return True
        except Exception as e:
            # Mercilessly swallow Telegram errors to keep the scraper running
            logger.error(f"AlertService failed to send to Telegram: {type(e).__name__}")
            return False
