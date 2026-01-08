from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.database import InviteCode


class InviteService:
    """Service for creating and validating invite tokens."""

    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def _generate_unique_code(self) -> str:
        for _ in range(5):
            code = secrets.token_urlsafe(6)[:8]
            result = await self.db.execute(select(InviteCode).where(InviteCode.code == code))
            if result.scalar_one_or_none() is None:
                return code
        raise HTTPException(status_code=500, detail="Failed to generate unique invite code")

    async def create_invite(
        self,
        email: str,
        never_expires: bool,
    ) -> Tuple[InviteCode, str]:
        if never_expires and not self.settings.allow_indefinite_invites:
            raise HTTPException(status_code=400, detail="Indefinite invites are disabled")

        now = datetime.utcnow()
        token = secrets.token_urlsafe(32)
        token_hash = self.hash_token(token)
        expires_at = None
        if not never_expires:
            expires_at = now + timedelta(hours=self.settings.invite_ttl_hours)

        code = await self._generate_unique_code()
        normalized = self.normalize_email(email)

        invite = InviteCode(
            code=code,
            invite_email=email,
            invite_email_normalized=normalized,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(invite)
        await self.db.flush()
        return invite, token

    async def get_valid_invite(self, invite_token: str) -> Optional[InviteCode]:
        token_hash = self.hash_token(invite_token)
        now = datetime.utcnow()
        result = await self.db.execute(
            select(InviteCode).where(
                InviteCode.token_hash == token_hash,
                InviteCode.is_used.is_(False),
                InviteCode.revoked_at.is_(None),
                ((InviteCode.expires_at.is_(None)) | (InviteCode.expires_at > now)),
            )
        )
        return result.scalar_one_or_none()
