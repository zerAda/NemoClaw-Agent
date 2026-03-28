"""AlertService tests — mock Telegram Bot."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.alerter import AlertService

@pytest.mark.asyncio
async def test_alert_message_format():
    """SCRAPE-05: send_alert calls Bot.send_message with platform + severity."""
    mock_bot_instance = AsyncMock()
    mock_bot_cls = MagicMock(return_value=mock_bot_instance)

    with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "tok123", "NEMO_AUTH_USER_ID": "999"}):
        with patch("src.alerter.Bot", mock_bot_cls):
            alerter = AlertService()
            await alerter.send_alert("LinkedIn", "possible block")

    mock_bot_instance.send_message.assert_called_once()
    call_kwargs = mock_bot_instance.send_message.call_args.kwargs
    text = call_kwargs.get("text", "")
    
    assert "LinkedIn" in text
    assert "possible block" in text
    assert "Severity: CRITICAL" in text

@pytest.mark.asyncio
async def test_alert_swallows_exception():
    """SCRAPE-05: send_alert does not raise if Bot.send_message throws."""
    mock_bot_instance = AsyncMock()
    mock_bot_instance.send_message.side_effect = Exception("Network error")
    mock_bot_cls = MagicMock(return_value=mock_bot_instance)

    with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "tok", "NEMO_AUTH_USER_ID": "1"}):
        with patch("src.alerter.Bot", mock_bot_cls):
            alerter = AlertService()
            # Must not raise
            await alerter.send_alert("France Travail", "timeout")

@pytest.mark.asyncio
async def test_alert_skips_if_no_credentials():
    """SCRAPE-05: send_alert logs info and returns if creds missing."""
    with patch.dict("os.environ", {}, clear=True):
        alerter = AlertService()
        # Must not raise, must return False
        result = await alerter.send_alert("LinkedIn", "test")
        assert result is False
