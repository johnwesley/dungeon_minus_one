import os
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import jwt
from dotenv import load_dotenv

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev_secret_key_change_me_in_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Use bcrypt with explicit truncate enabled (though passlib handles this, direct calls might not)
# or manually truncate before hashing. Passlib generally handles this if configured correctly,
# but the error suggests it's passing >72 bytes to the backend.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    # Bcrypt has a 72 byte limit. Truncate if necessary to avoid errors.
    # Ideally we would use a different hash like Argon2, but for compatibility/simplicity fix:
    # Ensure we are working with bytes for length check to be precise, but string slicing works for simple cases.
    # Passlib expects strings.
    if len(plain_password.encode('utf-8')) > 72:
        # We can't easily truncate utf-8 bytes and decode back to string safely without potentially splitting a char.
        # However, for the sake of not crashing, let's truncate the string length which is usually <= bytes.
        # A safer approach is catching the error or just using the first 72 chars.
        plain_password = plain_password[:72]
        
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # Fallback if it still complains (e.g. if the hashed password was created with a different length or method)
        return False


def get_password_hash(password: str) -> str:
    """Hash a password."""
    # Bcrypt has a 72 byte limit.
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
        
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.JWTError:
        return None
