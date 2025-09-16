from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import cast, String  # <- ADICIONE
from .config import settings
from .db import get_db
from .models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
  try:
    payload = jwt.decode(token, settings.JWT_SECRET,
                         algorithms=[settings.JWT_ALG])
    sub: str = payload.get("sub")
    if not sub:
      raise ValueError
  except (JWTError, ValueError):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

  user = db.query(User).filter(cast(User.id, String) == sub).first()
  if not user:
    raise HTTPException(status_code=401, detail="User not found")
  return user
