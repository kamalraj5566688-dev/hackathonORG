import os
import datetime
from passlib.context import CryptContext
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ============================================================
# SECURITY CONFIGURATION
# ============================================================

# Secret key for signing JWTs. In production, load this from an environment variable!
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-development-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Configure Passlib to use Argon2id, the current best-practice hashing algorithm
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security = HTTPBearer()


# ============================================================
# PASSWORD HASHING
# ============================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against its Argon2id hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generates an Argon2id hash for a given password."""
    return pwd_context.hash(password)


# ============================================================
# JWT TOKEN MANAGEMENT
# ============================================================

def create_access_token(data: dict, expires_delta: datetime.timedelta = None) -> str:
    """Creates a signed JSON Web Token (JWT) for user sessions."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Dependency to verify the JWT token from the Authorization header.
    Returns the decoded token payload if valid, otherwise raises a 401 Unauthorized.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")