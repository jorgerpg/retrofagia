from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..deps import get_current_user
from ..models import Comment, Verb, ObjType, Record
from ..schemas import CommentIn, CommentOut
from ..activity import create_activity
from sqlalchemy import cast, String

router = APIRouter(prefix="/records", tags=["comments"])


@router.post("/{record_id}/comments", response_model=CommentOut)
def create_comment(record_id: str, payload: CommentIn,
                   db: Session = Depends(get_db), user=Depends(get_current_user)):
  rec = db.query(Record).filter(cast(Record.id, String) == record_id).first()
  if not rec:
    raise HTTPException(status_code=404, detail="record não encontrado")
  c = Comment(user_id=user.id, record_id=rec.id, content=payload.content)
  db.add(c)
  db.commit()
  db.refresh(c)
  create_activity(db, user.id, Verb.COMMENT, ObjType.COMMENT, c.id)
  return c


@router.get("/{record_id}/comments", response_model=list[CommentOut])
def list_comments(record_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
  return db.query(Comment).filter(cast(Comment.record_id, String) == record_id).order_by(Comment.created_at.desc()).all()
