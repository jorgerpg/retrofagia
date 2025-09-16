from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Review, Verb, ObjType
from ..deps import get_current_user
from ..activity import create_activity
from ..schemas import ReviewIn, ReviewOut


router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewOut)
def upsert_review(payload: ReviewIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
  r = db.query(Review).filter(
      Review.user_id == user.id,
      Review.record_id == payload.record_id
  ).first()

  if r:
    r.rating = payload.rating
    r.comment = payload.comment
  else:
    r = Review(
        user_id=user.id,
        record_id=payload.record_id,
        rating=payload.rating,
        comment=payload.comment
    )
    db.add(r)

  db.commit()
  db.refresh(r)
  create_activity(db, user.id, Verb.REVIEW, ObjType.REVIEW, r.id)
  return r
