from ..deps import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User
from ..schemas import UserCreate, TokenOut
from ..security import hash_password, verify_password, create_access_token
from pydantic import BaseModel


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut)
def register(data: UserCreate, db: Session = Depends(get_db)):
  if db.query(User).filter((User.username == data.username) | (User.email == data.email)).first():
    raise HTTPException(status_code=400, detail="username/email já usados")
  u = User(username=data.username, email=data.email,
           password_hash=hash_password(data.password))
  db.add(u)
  db.commit()
  db.refresh(u)
  return TokenOut(access_token=create_access_token(str(u.id)))


class LoginIn(BaseModel):
  username_or_email: str
  password: str


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
  q = db.query(User).filter((User.username == data.username_or_email)
                            | (User.email == data.username_or_email))
  user = q.first()
  if not user or not verify_password(data.password, user.password_hash):
    raise HTTPException(status_code=400, detail="credenciais inválidas")
  return TokenOut(access_token=create_access_token(str(user.id)))


@router.get("/me")
def me(user=Depends(get_current_user)):
  return {"id": str(user.id), "username": user.username, "email": user.email}
