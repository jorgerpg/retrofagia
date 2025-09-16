from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from .config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(p: str) -> str:
  return pwd_context.hash(p)


def verify_password(p: str, hashed: str) -> bool:
  return pwd_context.verify(p, hashed)


def create_access_token(sub: str, expires_minutes: int | None = None) -> str:
  expire = datetime.utcnow() + \
      timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
  return jwt.encode({"sub": sub, "exp": expire}, settings.JWT_SECRET, algorithm=settings.JWT_ALG)
