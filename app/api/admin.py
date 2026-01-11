from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.auth_schemas import (
    InviteExtend,
    InviteRequestDecision,
    InviteRequestResponse,
    UserExtend,
    UserResponse,
    UserSuspend,
)
from app.models.database import InviteCode, InviteRequest, User
from app.services.email_service import EmailService
from app.services.invite_service import InviteService
from app.services.session_service import SessionService

router = APIRouter(prefix="/admin")


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all users with optional filtering by status and search."""
    query = select(User)

    if status == "active":
        query = query.where(
            User.is_active == True,
            User.suspended_at.is_(None),
            User.deleted_at.is_(None),
        )
    elif status == "suspended":
        query = query.where(User.suspended_at.isnot(None))
    elif status == "deleted":
        query = query.where(User.deleted_at.isnot(None))

    if search:
        search_term = f"%{search}%"
        query = query.where(
            (User.username.ilike(search_term)) | (User.email.ilike(search_term))
        )

    result = await db.execute(query.order_by(User.created_at.desc()))
    users = result.scalars().all()

    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            suspended_at=user.suspended_at,
            suspended_reason=user.suspended_reason,
            deleted_at=user.deleted_at,
            expires_at=user.expires_at,
        )
        for user in users
    ]


@router.get("/invite-requests", response_model=list[InviteRequestResponse])
async def list_invite_requests(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = select(InviteRequest)
    if status:
        query = query.where(InviteRequest.status == status)
    result = await db.execute(query.order_by(InviteRequest.requested_at.desc()))
    requests = result.scalars().all()

    return [
        InviteRequestResponse(
            id=req.id,
            email=req.email,
            status=req.status,
            requested_at=req.requested_at,
            approved_at=req.approved_at,
            rejected_at=req.rejected_at,
            invite_id=req.invite_id,
            notes=req.notes,
        )
        for req in requests
    ]


@router.post("/invite-requests/{request_id}/approve")
async def approve_invite_request(
    request_id: str,
    decision: InviteRequestDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    settings = get_settings()
    invite_request = await db.get(InviteRequest, request_id)
    if not invite_request:
        raise HTTPException(status_code=404, detail="Invite request not found")
    if invite_request.status != "pending":
        raise HTTPException(status_code=400, detail="Invite request already processed")

    invite_service = InviteService(db, settings)
    invite, token = await invite_service.create_invite(invite_request.email, decision.never_expires)

    invite_request.status = "approved"
    invite_request.approved_at = datetime.utcnow()
    invite_request.approved_by_user_id = current_user.id
    invite_request.invite_id = invite.id
    invite_request.notes = decision.notes

    send_email = decision.send_email and settings.invite_email_send_mode == "auto"
    if send_email:
        email_service = EmailService()
        try:
            await email_service.send_invite_email(invite.invite_email, token)
            invite.sent_at = datetime.utcnow()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Email send failed: {e}")
        return {"sent": True, "invite_id": invite.id}

    return {"sent": False, "invite_token": token, "invite_id": invite.id}


@router.post("/invite-requests/{request_id}/reject")
async def reject_invite_request(
    request_id: str,
    decision: InviteRequestDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    invite_request = await db.get(InviteRequest, request_id)
    if not invite_request:
        raise HTTPException(status_code=404, detail="Invite request not found")
    if invite_request.status != "pending":
        raise HTTPException(status_code=400, detail="Invite request already processed")

    invite_request.status = "rejected"
    invite_request.rejected_at = datetime.utcnow()
    invite_request.approved_by_user_id = current_user.id
    invite_request.notes = decision.notes

    return {"status": "rejected"}


@router.post("/invite-requests/{request_id}/regenerate")
async def regenerate_invite_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Regenerate an invite for an already approved request (e.g. lost token)."""
    settings = get_settings()
    invite_request = await db.get(InviteRequest, request_id)
    if not invite_request:
        raise HTTPException(status_code=404, detail="Invite request not found")
    if invite_request.status != "approved":
        raise HTTPException(status_code=400, detail="Can only regenerate approved requests")

    # Revoke old invite if it exists
    if invite_request.invite_id:
        old_invite = await db.get(InviteCode, invite_request.invite_id)
        if old_invite:
            old_invite.revoked_at = datetime.utcnow()

    # Create new invite
    invite_service = InviteService(db, settings)
    # Defaulting to standard expiration logic, or could infer from old invite if needed
    # For simplicity, we treat it as a fresh invite.
    invite, token = await invite_service.create_invite(invite_request.email, never_expires=False)

    # Update request record
    invite_request.invite_id = invite.id
    invite_request.approved_at = datetime.utcnow()
    invite_request.approved_by_user_id = current_user.id
    invite_request.notes = (invite_request.notes or "") + "\n[Regenerated]"

    return {"sent": False, "invite_token": token, "invite_id": invite.id}


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    payload: UserSuspend,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.suspended_at = datetime.utcnow()
    user.suspended_reason = payload.reason
    user.is_active = False

    session_service = SessionService(db, get_settings())
    await session_service.revoke_user_sessions(user_id)

    return {"status": "suspended"}


@router.post("/users/{user_id}/unsuspend")
async def unsuspend_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.suspended_at = None
    user.suspended_reason = None
    user.is_active = True

    return {"status": "active"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.deleted_at = datetime.utcnow()

    session_service = SessionService(db, get_settings())
    await session_service.revoke_user_sessions(user_id)

    return {"status": "deleted"}


@router.post("/users/{user_id}/extend")
async def extend_user(
    user_id: str,
    payload: UserExtend,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.expires_at = payload.expires_at
    return {"status": "updated", "expires_at": user.expires_at}


@router.post("/invites/{invite_id}/revoke")
async def revoke_invite(
    invite_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    invite = await db.get(InviteCode, invite_id)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    invite.revoked_at = datetime.utcnow()
    return {"status": "revoked"}


@router.post("/invites/{invite_id}/extend")
async def extend_invite(
    invite_id: str,
    payload: InviteExtend,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    invite = await db.get(InviteCode, invite_id)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    invite.expires_at = payload.expires_at
    return {"status": "updated", "expires_at": invite.expires_at}
