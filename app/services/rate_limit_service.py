from __future__ import annotations

from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.database import RateLimitEntry


def _parse_networks(value: Optional[str]) -> list:
    if not value:
        return []
    networks = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            networks.append(ip_network(item, strict=False))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid CIDR/IP in allowlist: {item}",
            ) from exc
    return networks


def _ip_in_networks(ip_value: str, networks: list) -> bool:
    try:
        ip_obj = ip_address(ip_value)
    except ValueError:
        return False
    return any(ip_obj in network for network in networks)


def _first_forwarded_ip(value: str) -> Optional[str]:
    for item in value.split(","):
        item = item.strip()
        if item:
            return item
    return None


def get_client_ip(request: Request) -> Optional[str]:
    settings = get_settings()
    remote_ip = request.client.host if request.client else None
    if not remote_ip:
        return None

    if not settings.trust_proxy_headers or not settings.trusted_proxy_ips:
        return remote_ip

    trusted_proxies = _parse_networks(settings.trusted_proxy_ips)
    if not _ip_in_networks(remote_ip, trusted_proxies):
        return remote_ip

    forwarded_for = request.headers.get("x-forwarded-for", "")
    forwarded_ip = _first_forwarded_ip(forwarded_for)
    if forwarded_ip:
        try:
            ip_address(forwarded_ip)
            return forwarded_ip
        except ValueError:
            return remote_ip

    return remote_ip


async def enforce_invite_allowlist(request: Request) -> str:
    settings = get_settings()
    client_ip = get_client_ip(request)

    if not settings.invite_ip_allowlist:
        return client_ip or ""

    allowlist = _parse_networks(settings.invite_ip_allowlist)
    if not client_ip or not _ip_in_networks(client_ip, allowlist):
        raise HTTPException(status_code=403, detail="Invite generation is restricted")

    return client_ip


async def enforce_invite_rate_limit(db: AsyncSession, client_ip: Optional[str]) -> None:
    settings = get_settings()
    max_requests = settings.invite_rate_limit_max
    window_seconds = settings.invite_rate_limit_window_seconds
    if max_requests <= 0 or window_seconds <= 0:
        return

    identifier = client_ip or "unknown"
    await _enforce_rate_limit(db, f"invite:{identifier}", max_requests, window_seconds)


async def _enforce_rate_limit(
    db: AsyncSession,
    key_prefix: str,
    max_requests: int,
    window_seconds: int,
) -> None:
    now = datetime.utcnow()
    window_epoch = int(now.timestamp() // window_seconds) * window_seconds
    window_start = datetime.utcfromtimestamp(window_epoch)
    expires_at = window_start + timedelta(seconds=window_seconds)
    key = f"{key_prefix}:{window_epoch}"

    count = await _increment_rate_limit(db, key, window_start, expires_at)
    await db.execute(delete(RateLimitEntry).where(RateLimitEntry.expires_at < now))

    if count > max_requests:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


async def _increment_rate_limit(
    db: AsyncSession,
    key: str,
    window_start: datetime,
    expires_at: datetime,
) -> int:
    values = {
        "key": key,
        "count": 1,
        "window_start": window_start,
        "expires_at": expires_at,
    }

    bind = db.get_bind()
    dialect = bind.dialect.name if bind else ""

    if dialect == "postgresql":
        stmt = (
            pg_insert(RateLimitEntry)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[RateLimitEntry.key],
                set_={"count": RateLimitEntry.count + 1},
            )
            .returning(RateLimitEntry.count)
        )
        result = await db.execute(stmt)
        return int(result.scalar_one())

    stmt = (
        sqlite_insert(RateLimitEntry)
        .values(**values)
        .on_conflict_do_update(
            index_elements=[RateLimitEntry.key],
            set_={"count": RateLimitEntry.count + 1},
        )
    )
    await db.execute(stmt)
    result = await db.execute(select(RateLimitEntry.count).where(RateLimitEntry.key == key))
    return int(result.scalar_one())
