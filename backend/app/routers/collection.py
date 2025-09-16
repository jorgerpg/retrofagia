from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import UserCollection, Record, Verb, ObjType, User
from ..deps import get_current_user
from ..activity import create_activity
from ..schemas import FavoriteUpdate, RecordInCollectionOut
from sqlalchemy import cast, String
from uuid import UUID


router = APIRouter(prefix="/collection", tags=["collection"])


@router.post("/{record_id}")
def add_to_collection(record_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
  link = UserCollection(user_id=user.id, record_id=record_id)
  db.merge(link)
  db.commit()
  create_activity(db, user.id, Verb.ADD_RECORD, ObjType.RECORD, record_id)
  return {"status": "ok"}


@router.get("/me")
def my_collection(db: Session = Depends(get_db), user=Depends(get_current_user)):
  return db.query(Record).join(UserCollection, UserCollection.record_id == Record.id).filter(UserCollection.user_id == user.id).all()


@router.patch("/{record_id}")
def update_favorite(record_id: str, data: FavoriteUpdate,
                    db: Session = Depends(get_db), user=Depends(get_current_user)):
  link = db.query(UserCollection)\
           .filter(UserCollection.user_id == user.id,
                   cast(UserCollection.record_id, String) == record_id)\
           .first()
  if not link:
    raise HTTPException(status_code=404, detail="não está na coleção")
  link.is_favorite = data.is_favorite
  db.commit()
  return {"status": "ok", "is_favorite": link.is_favorite}


@router.get("/me/favorites")
def my_favorites(db: Session = Depends(get_db), user=Depends(get_current_user)):
  return db.query(Record)\
      .join(UserCollection, UserCollection.record_id == Record.id)\
      .filter(UserCollection.user_id == user.id, UserCollection.is_favorite == True)\
      .all()


@router.get("/me", response_model=list[RecordInCollectionOut])
def list_my_collection(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
  rows = (
      db.query(
          Record,
          UserCollection.is_favorite,
          UserCollection.added_at,
          UserCollection.condition,
      )
      .join(UserCollection, UserCollection.record_id == Record.id)
      .filter(UserCollection.user_id == current_user.id)
      .order_by(desc(UserCollection.added_at))
      .all()
  )

  # montamos cada item como Record + flags
  result = []
  for rec, is_fav, added_at, condition in rows:
    base = RecordInCollectionOut.model_validate(rec).model_dump()
    base.update(
        {"is_favorite": is_fav, "added_at": added_at, "condition": condition}
    )
    result.append(base)
  return result


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_collection(record_id: UUID,
                           db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
  link = (db.query(UserCollection)
            .filter(UserCollection.user_id == current_user.id,
                    UserCollection.record_id == record_id)
            .first())
  if not link:
    # idempotente: 204 mesmo se já não estiver
    return
  db.delete(link)
  db.commit()
  return
