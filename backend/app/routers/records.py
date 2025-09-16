from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..db import get_db
from ..models import Record
from ..schemas import RecordCreate, RecordOut
from ..deps import get_current_user


router = APIRouter(prefix="/records", tags=["records"])


@router.post("")
def create_record(payload: RecordCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
  if db.query(Record).filter(Record.matrix_code == payload.matrix_code).first():
    raise HTTPException(status_code=400, detail="matrix_code já existe")
  r = Record(**payload.dict(), created_by=user.id)
  db.add(r)
  db.commit()
  db.refresh(r)
  return r


@router.get("")
def search(q: str | None = None, code: str | None = None, artist: str | None = None, db: Session = Depends(get_db)):
  query = db.query(Record)
  if code:
    query = query.filter(Record.matrix_code == code)
  if q:
    like = f"%{q}%"
    query = query.filter(
        or_(Record.title.ilike(like), Record.artist.ilike(like)))
  if artist:
    query = query.filter(Record.artist.ilike(f"%{artist}%"))
  return query.order_by(Record.created_at.desc()).limit(50).all()


@router.get("", response_model=list[RecordOut])
def search(q: str | None = None, code: str | None = None, artist: str | None = None,
           year: int | None = None, genre: str | None = None, label: str | None = None,
           db: Session = Depends(get_db), user=Depends(get_current_user)):
  query = db.query(Record)
  if code:
    query = query.filter(Record.matrix_code == code)
  if q:
    like = f"%{q}%"
    query = query.filter(
        or_(Record.title.ilike(like), Record.artist.ilike(like)))
  if artist:
    query = query.filter(Record.artist.ilike(f"%{artist}%"))
  if year is not None:
    query = query.filter(Record.year == year)
  if genre:
    query = query.filter(Record.genre.ilike(f"%{genre}%"))
  if label:
    query = query.filter(Record.label.ilike(f"%{label}%"))
  return query.order_by(Record.created_at.desc()).limit(50).all()
