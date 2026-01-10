from __future__ import annotations

from typing import Optional

import httpx

from app.config import get_settings


POSTMARK_URL = "https://api.postmarkapp.com/email"


class EmailService:
    """Send transactional emails via Postmark."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def send_invite_email(self, to_email: str, invite_token: str) -> None:
        if not self.settings.postmark_server_token or not self.settings.postmark_from_email:
            raise RuntimeError("Postmark is not configured")
        if not self.settings.public_app_url:
            raise RuntimeError("PUBLIC_APP_URL is not configured")

        app_url = self.settings.public_app_url.rstrip("/")
        invite_link = f"{app_url}/register.html?invite_token={invite_token}"

        subject = "Your Dungeon -1 invite"
        text_body = (
            "You have been approved for access to Dungeon -1.\n\n"
            f"Invite token: {invite_token}\n"
            f"Register here: {invite_link}\n\n"
            "This invite expires in 24 hours unless noted otherwise."
        )

        payload = {
            "From": self.settings.postmark_from_email,
            "To": to_email,
            "Subject": subject,
            "TextBody": text_body,
            "MessageStream": self.settings.postmark_message_stream,
        }

        headers = {
            "X-Postmark-Server-Token": self.settings.postmark_server_token,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(POSTMARK_URL, json=payload, headers=headers)
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("Message", response.text)
                except Exception:
                    pass
                raise RuntimeError(f"Postmark error ({response.status_code}): {error_detail}")
