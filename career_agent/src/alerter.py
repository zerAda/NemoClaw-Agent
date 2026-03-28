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
        """Diamond-Grade: Send an urgent alert for failures or blocks."""
        return await self._push(f"🚨 SCRAPER ALERT [{platform}]\n\nIssue: {message}\nSeverity: CRITICAL")

    async def send_info(self, message: str) -> bool:
        """Standard status update for cycle progress."""
        return await self._push(f"🤖 NemoClaw Status\n\n{message}")

    async def send_summary(self, stats: dict) -> bool:
        """Daily summary report formatted for Telegram readability."""
        msg = "📊 Daily Autonomous Summary\n\n"
        msg += f"• Total Scanned: {stats.get('total', 0)}\n"
        msg += f"• Ready: {stats.get('READY', 0)}\n"
        msg += f"• Skipped: {stats.get('SKIPPED', 0)}\n"
        msg += f"• Errors: {stats.get('ABANDONED', 0)}\n\n"
        msg += "Use /status for real-time details."
        return await self._push(msg)

    async def _push(self, text: str) -> bool:
        """Internal delivery engine with merciless error suppression."""
        if not self.token or not self.chat_id or Bot is None:
            logger.info(f"[TELEGRAM OFFLINE] {text}")
            return False

        try:
            bot = Bot(token=self.token)
            await bot.send_message(chat_id=self.chat_id, text=text)
            return True
        except Exception as e:
            logger.error(f"AlertService failed to push: {type(e).__name__}: {e}")
            return False
