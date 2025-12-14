from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.database import User, InviteCode
from app.models.auth_schemas import UserLogin, UserRegister, Token, InviteCreate
from app.services.auth_service import verify_password, get_password_hash, create_access_token, decode_access_token
from app.config import get_settings
from fastapi.security import OAuth2PasswordBearer
import uuid

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    settings = get_settings()
    
    # Dev bypass logic
    if settings.dev_auth_bypass and token == "dev_secret_key_change_me_in_prod":
        # Return a dummy or admin user if bypassing
        # Ideally, we should fetch a real user or mock one. 
        # For simplicity, let's try to get the first user or create a temp one.
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if user:
            return user
        # Fallback if no users exist yet (shouldn't happen if setup ran)
        return User(id="dev_user", username="dev", is_admin=True)

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


@router.get("/dev-mode")
async def check_dev_mode():
    """Check if dev mode is enabled (for pre-filling login form)."""
    settings = get_settings()
    return {"enabled": settings.dev_auth_bypass}


@router.post("/register", response_model=Token)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check invite code
    result = await db.execute(select(InviteCode).where(InviteCode.code == data.invite_code, InviteCode.is_used == False))
    invite = result.scalar_one_or_none()
    
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid or expired invite code")
        
    # Check existing user
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")
        
    # Create user
    new_user = User(
        username=data.username,
        hashed_password=get_password_hash(data.password)
    )
    db.add(new_user)
    await db.flush()  # Get ID
    
    # Mark invite used
    invite.is_used = True
    invite.used_at = datetime.utcnow()
    invite.used_by_user_id = new_user.id
    
    await db.commit()
    
    # Create token
    access_token = create_access_token(data={"sub": new_user.id, "username": new_user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": user.id, "username": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/invite/generate")
async def generate_invite(data: InviteCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Simple admin check: first user is admin, or check flag
    if not current_user.is_admin:
        # Allow if it's the very first user (bootstrapping) or if explicit admin
        # For now, we'll be lenient for testing or strict. Let's rely on a hardcoded check or just is_admin
        raise HTTPException(status_code=403, detail="Admin privileges required")

    code = data.code or str(uuid.uuid4())[:8]
    
    # Check collision
    result = await db.execute(select(InviteCode).where(InviteCode.code == code))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Code already exists")
        
    invite = InviteCode(code=code)
    db.add(invite)
    await db.commit()
    
    return {"code": code}

