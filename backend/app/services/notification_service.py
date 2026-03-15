"""Notification service — stores notifications in DB and optionally sends to Discord."""
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.services.settings_service import get_setting

logger = logging.getLogger(__name__)


async def notify(
    db: AsyncSession,
    title: str,
    message: str,
    notification_type: str = "info",
) -> Notification:
    """Create a notification in the DB and optionally send to Discord webhook.

    Args:
        db: Database session.
        title: Short notification title.
        message: Notification body/details.
        notification_type: One of 'info', 'success', 'warning', 'error'.

    Returns:
        The created Notification record.
    """
    # Store in database
    notif = Notification(
        title=title,
        message=message,
        notification_type=notification_type,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)

    # Send to Discord webhook if configured
    webhook_url = await get_setting(db, "notifications.discord_webhook_url")
    if webhook_url:
        await _send_discord(webhook_url, title, message, notification_type)

    return notif


# Colour mapping for Discord embed sidebar
_DISCORD_COLORS = {
    "info": 0x3498DB,       # blue
    "success": 0x2ECC71,    # green
    "warning": 0xF39C12,    # orange
    "error": 0xE74C3C,      # red
}


async def _send_discord(
    webhook_url: str,
    title: str,
    message: str,
    notification_type: str,
) -> None:
    """POST a Discord webhook message with an embed."""
    color = _DISCORD_COLORS.get(notification_type, 0x95A5A6)
    payload = {
        "embeds": [
            {
                "title": title,
                "description": message,
                "color": color,
            }
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code >= 400:
                logger.warning(
                    "Discord webhook returned %d: %s", resp.status_code, resp.text[:200]
                )
    except Exception:
        logger.warning("Failed to send Discord notification", exc_info=True)
