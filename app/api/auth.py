from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.auth_schemas import (
    AuthSessionResponse,
    InviteCreate,
    InviteRequestCreate,
    UserLogin,
    UserRegister,
)
from app.models.database import InviteRequest, User
from app.services.auth_service import get_password_hash, verify_password
from app.services.captcha_service import verify_turnstile
from app.services.email_service import EmailService
from app.services.invite_service import InviteService
from app.services.rate_limit_service import (
    enforce_invite_allowlist,
    enforce_invite_rate_limit,
    enforce_invite_request_rate_limit,
    enforce_login_rate_limit,
    enforce_register_rate_limit,
    get_client_ip,
)
from app.services.session_service import SessionService

router = APIRouter()


def _set_session_cookie(response: Response, settings, session_id: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        session_id,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        domain=settings.session_cookie_domain,
        path="/",
    )


def _clear_session_cookie(response: Response, settings) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        domain=settings.session_cookie_domain,
        path="/",
    )


async def _enforce_user_status(
    user: User,
    session_id: Optional[str],
    session_service: SessionService,
    response: Optional[Response],
) -> None:
    now = datetime.utcnow()
    if not user.is_active or user.suspended_at or user.deleted_at:
        if session_id:
            await session_service.revoke_session(session_id)
        if response:
            _clear_session_cookie(response, get_settings())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")

    if user.expires_at and user.expires_at <= now:
        if session_id:
            await session_service.revoke_session(session_id)
        if response:
            _clear_session_cookie(response, get_settings())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account expired")


async def get_current_user(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> User:
    settings = get_settings()

    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    session_service = SessionService(db, settings)
    session, user = await session_service.validate_session(session_id)
    if not session or not user:
        _clear_session_cookie(response, settings)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    await _enforce_user_status(user, session_id, session_service, response)

    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        csrf_token = request.headers.get("x-csrf-token")
        if not session_service.verify_csrf(session, csrf_token):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing or invalid")

    return user


@router.get("/turnstile-key")
async def get_turnstile_key():
    settings = get_settings()
    return {"site_key": settings.turnstile_site_key}


@router.post("/invite-request")
async def invite_request(
    data: InviteRequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = get_client_ip(request)
    await enforce_invite_request_rate_limit(db, client_ip, data.email)

    settings = get_settings()
    if settings.turnstile_secret_key:
        if not data.turnstile_token:
            raise HTTPException(status_code=400, detail="Captcha token missing")
        if not await verify_turnstile(data.turnstile_token, client_ip):
            raise HTTPException(status_code=400, detail="Captcha verification failed")

    invite_request = InviteRequest(
        email=data.email,
        email_normalized=data.email.strip().lower(),
        status="pending",
        requested_at=datetime.utcnow(),
        captcha_verified_at=datetime.utcnow(),
        ip=client_ip,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(invite_request)
    return {"status": "ok"}


@router.post("/register", response_model=AuthSessionResponse)
async def register(data: UserRegister, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    invite_service = InviteService(db, settings)

    invite = await invite_service.get_valid_invite(data.invite_token)
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid or expired invite token")

    if not invite.invite_email:
        raise HTTPException(status_code=400, detail="Invite is missing email binding")

    client_ip = get_client_ip(request)
    invite_token_hash = invite_service.hash_token(data.invite_token)
    await enforce_register_rate_limit(db, client_ip, invite_token_hash)

    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    normalized_email = invite.invite_email_normalized or invite_service.normalize_email(invite.invite_email)
    result = await db.execute(select(User).where(User.email_normalized == normalized_email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    expires_at = None
    if settings.default_account_expires:
        expires_at = datetime.utcnow() + timedelta(days=settings.account_ttl_days)

    new_user = User(
        username=data.username,
        email=invite.invite_email,
        email_normalized=normalized_email,
        hashed_password=get_password_hash(data.password),
        expires_at=expires_at,
    )
    db.add(new_user)
    await db.flush()

    invite.is_used = True
    invite.used_at = datetime.utcnow()
    invite.used_by_user_id = new_user.id

    session_service = SessionService(db, settings)
    session_id, csrf_token, session = await session_service.create_session(
        new_user.id,
        client_ip,
        request.headers.get("user-agent"),
    )
    _set_session_cookie(response, settings, session_id)

    return AuthSessionResponse(
        authenticated=True,
        username=new_user.username,
        is_admin=new_user.is_admin,
        account_expires_at=new_user.expires_at,
        session_expires_at=session.expires_at,
        csrf_token=csrf_token,
    )


@router.post("/login", response_model=AuthSessionResponse)
async def login(data: UserLogin, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    identifier = data.identifier.strip()
    normalized = identifier.lower()

    client_ip = get_client_ip(request)
    await enforce_login_rate_limit(db, client_ip, normalized)

    result = await db.execute(
        select(User).where(or_(User.username == identifier, User.email_normalized == normalized))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_service = SessionService(db, settings)
    await _enforce_user_status(user, None, session_service, None)

    session_id, csrf_token, session = await session_service.create_session(
        user.id,
        client_ip,
        request.headers.get("user-agent"),
    )
    _set_session_cookie(response, settings, session_id)

    return AuthSessionResponse(
        authenticated=True,
        username=user.username,
        is_admin=user.is_admin,
        account_expires_at=user.expires_at,
        session_expires_at=session.expires_at,
        csrf_token=csrf_token,
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        session_service = SessionService(db, settings)
        await session_service.revoke_session(session_id)
    _clear_session_cookie(response, settings)
    return {"ok": True}


@router.get("/session", response_model=AuthSessionResponse)
async def session_info(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        return AuthSessionResponse(authenticated=False)

    session_service = SessionService(db, settings)
    session, user = await session_service.validate_session(session_id)
    if not session or not user:
        _clear_session_cookie(response, settings)
        return AuthSessionResponse(authenticated=False)

    await _enforce_user_status(user, session_id, session_service, response)
    csrf_token = await session_service.rotate_csrf_token(session_id)

    return AuthSessionResponse(
        authenticated=True,
        username=user.username,
        is_admin=user.is_admin,
        account_expires_at=user.expires_at,
        session_expires_at=session.expires_at,
        csrf_token=csrf_token,
    )


@router.get("/csrf")
async def csrf_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    session_id = request.cookies.get(settings.session_cookie_name)
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    session_service = SessionService(db, settings)
    session, user = await session_service.validate_session(session_id)
    if not session or not user:
        _clear_session_cookie(response, settings)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    await _enforce_user_status(user, session_id, session_service, response)
    csrf_token = await session_service.rotate_csrf_token(session_id)
    return {"csrf_token": csrf_token}


@router.post("/invite/generate")
async def generate_invite(
    data: InviteCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    client_ip = await enforce_invite_allowlist(request)
    await enforce_invite_rate_limit(db, client_ip)

    settings = get_settings()
    invite_service = InviteService(db, settings)
    invite, token = await invite_service.create_invite(data.email, data.never_expires)

    send_email = data.send_email and settings.invite_email_send_mode == "auto"
    if send_email:
        email_service = EmailService()
        await email_service.send_invite_email(invite.invite_email, token)
        invite.sent_at = datetime.utcnow()
        return {"sent": True, "invite_id": invite.id}

    return {"invite_token": token, "invite_id": invite.id}
