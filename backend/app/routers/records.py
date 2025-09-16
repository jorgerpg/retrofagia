from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..db import get_db
from ..models import Record, User
from ..schemas import RecordCreate, RecordOut
from ..deps import get_current_user
from uuid import UUID
from PIL import Image
import io
import os


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


@router.put("/{record_id}/cover")
async def upload_cover(
    record_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # valida record existe
  rec = db.query(Record).filter(Record.id == record_id).first()
  if not rec:
    raise HTTPException(status_code=404, detail="record não encontrado")

  # valida mime
  if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
    raise HTTPException(
        status_code=400, detail="formato inválido (use jpg/png/webp)")

  # lê e converte para WEBP
  raw = await file.read()
  try:
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    # (opcional) limitar lado maior a 1200px
    im.thumbnail((1200, 1200))
  except Exception:
    raise HTTPException(status_code=400, detail="imagem inválida")

  path = f"uploads/covers/{record_id}.webp"
  im.save(path, format="WEBP", quality=85)

  # resposta simples (sem mexer em schemas/DB)
  return {"url": f"/uploads/covers/{record_id}.webp"}


@router.delete("/{record_id}/cover", status_code=204)
def delete_cover(record_id: UUID,
                 db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
  rec = db.query(Record).filter(Record.id == record_id).first()
  if not rec:
    raise HTTPException(status_code=404, detail="record não encontrado")
  path = f"uploads/covers/{record_id}.webp"
  try:
    if os.path.exists(path):
      os.remove(path)
  except Exception:
    raise HTTPException(status_code=500, detail="erro ao remover a capa")
  return
