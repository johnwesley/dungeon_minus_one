"""Async email service for sending feedback notifications."""

import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Async email service using aiosmtplib."""

    def __init__(self):
        self.settings = get_settings()

    def is_configured(self) -> bool:
        """Check if SMTP is properly configured for sending feedback."""
        return all([
            self.settings.smtp_host,
            self.settings.smtp_from_email,
            self.settings.feedback_recipient_email,
        ])

    async def send_feedback_email(
        self,
        username: str,
        rating: int,
        message: str,
    ) -> bool:
        """Send feedback email to configured recipient.

        Args:
            username: The player's username
            rating: Star rating (1-5)
            message: Feedback message text

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("SMTP not configured, skipping feedback email")
            return False

        # Build email
        msg = MIMEMultipart()
        msg["From"] = self.settings.smtp_from_email
        msg["To"] = self.settings.feedback_recipient_email
        msg["Subject"] = f"Dungeon -1 Feedback from {username} ({rating}/5 stars)"

        # Format body with star visualization
        stars = "\u2605" * rating + "\u2606" * (5 - rating)
        body = f"""Feedback from Dungeon -1
========================

Player: {username}
Rating: {stars} ({rating}/5)

Feedback:
{message}
"""
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=self.settings.smtp_host,
                port=self.settings.smtp_port,
                username=self.settings.smtp_username,
                password=self.settings.smtp_password,
                start_tls=self.settings.smtp_use_tls,
            )
            logger.info(f"Feedback email sent successfully from {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to send feedback email: {e}")
            return False
