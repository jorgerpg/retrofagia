# app/routers/reviews.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from ..deps import get_db, get_current_user
from ..models import Review, User
from ..schemas import ReviewCreate, ReviewOut

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewOut)
def create_or_update_review(payload: ReviewCreate,
                            db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
  rev = (db.query(Review)
           .filter(Review.user_id == current_user.id,
                   Review.record_id == payload.record_id)
           .first())
  if rev:
    rev.rating = payload.rating
    rev.comment = payload.comment
  else:
    rev = Review(user_id=current_user.id,
                 record_id=payload.record_id,
                 rating=payload.rating,
                 comment=payload.comment)
    db.add(rev)
  db.commit()
  db.refresh(rev)
  return rev


@router.get("/records/{record_id}/me", response_model=ReviewOut | None)
def get_my_review(record_id: UUID,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
  return (db.query(Review)
            .filter(Review.user_id == current_user.id,
                    Review.record_id == record_id)
            .first())
