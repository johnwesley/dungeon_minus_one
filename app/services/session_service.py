from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.database import User, UserSession


class SessionService:
    """Service for creating, validating, and revoking sessions."""

    def __init__(self, db: AsyncSession, settings: Settings):
        self.db = db
        self.settings = settings

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def create_session(
        self,
        user_id: str,
        ip: Optional[str],
        user_agent: Optional[str],
    ) -> Tuple[str, str, UserSession]:
        now = datetime.utcnow()
        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        expires_at = None

        if self.settings.session_absolute_ttl_days:
            expires_at = now + timedelta(days=self.settings.session_absolute_ttl_days)

        session = UserSession(
            id=session_id,
            user_id=user_id,
            created_at=now,
            last_seen_at=now,
            expires_at=expires_at,
            revoked_at=None,
            csrf_token_hash=self._hash_token(csrf_token),
            ip=ip,
            user_agent=user_agent,
        )
        self.db.add(session)
        await self.db.flush()
        return session_id, csrf_token, session

    async def validate_session(self, session_id: str) -> Tuple[Optional[UserSession], Optional[User]]:
        if not session_id:
            return None, None

        session = await self.db.get(UserSession, session_id)
        if not session:
            return None, None
        if session.revoked_at is not None:
            return None, None

        now = datetime.utcnow()
        if session.expires_at and session.expires_at <= now:
            await self.revoke_session(session.id)
            return None, None

        idle_timeout = timedelta(minutes=self.settings.session_idle_timeout_minutes)
        if session.last_seen_at and (now - session.last_seen_at) > idle_timeout:
            await self.revoke_session(session.id)
            return None, None

        # Optimization: Only update last_seen_at if > 60s to reduce DB writes
        if session.last_seen_at is None or (now - session.last_seen_at).total_seconds() > 60:
            session.last_seen_at = now

        user = await self.db.get(User, session.user_id)
        return session, user

    async def revoke_session(self, session_id: str) -> None:
        now = datetime.utcnow()
        await self.db.execute(
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(revoked_at=now)
        )

    async def revoke_user_sessions(self, user_id: str) -> None:
        now = datetime.utcnow()
        await self.db.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    def verify_csrf(self, session: UserSession, csrf_token: str) -> bool:
        if not csrf_token:
            return False
        return session.csrf_token_hash == self._hash_token(csrf_token)

    async def rotate_csrf_token(self, session_id: str) -> str:
        new_token = secrets.token_urlsafe(32)
        new_hash = self._hash_token(new_token)
        await self.db.execute(
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(csrf_token_hash=new_hash)
        )
        return new_token

    async def get_session(self, session_id: str) -> Optional[UserSession]:
        return await self.db.get(UserSession, session_id)
