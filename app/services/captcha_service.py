from __future__ import annotations

from typing import Optional

import httpx

from app.config import get_settings


TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile(token: str, remote_ip: Optional[str] = None) -> bool:
    settings = get_settings()
    if not settings.turnstile_secret_key:
        # Allow bypass in dev when Turnstile is not configured.
        return True

    data = {
        "secret": settings.turnstile_secret_key,
        "response": token,
    }
    if remote_ip:
        data["remoteip"] = remote_ip

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(TURNSTILE_VERIFY_URL, data=data)
        if response.status_code != 200:
            return False
        payload = response.json()
        return bool(payload.get("success"))
