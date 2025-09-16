from ..schemas import ActivityCommentIn, ActivityCommentOut
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import tuple_, cast, String
from ..db import get_db
from ..deps import get_current_user
from ..models import Activity, Follow, ActivityLike, ActivityComment

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("")
def get_feed(cursor_time: str | None = None, cursor_id: str | None = None, limit: int = 20,
             db: Session = Depends(get_db), user=Depends(get_current_user)):
  followees = [row[0] for row in db.query(Follow.followee_id).filter(
      Follow.follower_id == user.id).all()] + [user.id]
  q = db.query(Activity).filter(Activity.actor_id.in_(followees))
  if cursor_time and cursor_id:
    from datetime import datetime
    ct = datetime.fromisoformat(cursor_time)
    q = q.filter(tuple_(Activity.created_at, Activity.id) < (ct, cursor_id))
  items = q.order_by(Activity.created_at.desc(),
                     Activity.id.desc()).limit(limit).all()
  return items


@router.post("/{activity_id}/like", status_code=204)
def like(activity_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
  a = db.query(Activity).filter(
      cast(Activity.id, String) == activity_id).first()
  if not a:
    raise HTTPException(status_code=404, detail="activity não encontrada")
  db.merge(ActivityLike(activity_id=a.id, user_id=user.id))
  db.commit()


@router.delete("/{activity_id}/like", status_code=204)
def unlike(activity_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
  q = db.query(ActivityLike).filter(cast(ActivityLike.activity_id, String) == activity_id,
                                    ActivityLike.user_id == user.id)
  if q.first() is None:
    raise HTTPException(status_code=404, detail="like não existe")
  q.delete(synchronize_session=False)
  db.commit()


@router.post("/{activity_id}/comments", response_model=ActivityCommentOut)
def comment_activity(activity_id: str, payload: ActivityCommentIn,
                     db: Session = Depends(get_db), user=Depends(get_current_user)):
  a = db.query(Activity).filter(
      cast(Activity.id, String) == activity_id).first()
  if not a:
    raise HTTPException(status_code=404, detail="activity não encontrada")
  c = ActivityComment(activity_id=a.id, user_id=user.id,
                      content=payload.content)
  db.add(c)
  db.commit()
  db.refresh(c)
  return c


@router.get("/{activity_id}/comments", response_model=list[ActivityCommentOut])
def list_activity_comments(activity_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
  return db.query(ActivityComment).filter(cast(ActivityComment.activity_id, String) == activity_id)\
           .order_by(ActivityComment.created_at.desc()).all()
