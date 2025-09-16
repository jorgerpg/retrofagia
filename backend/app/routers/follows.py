from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..db import get_db
from ..deps import get_current_user
from ..models import Follow, Activity, Verb, ObjType, User
from sqlalchemy import and_, cast, String


router = APIRouter(prefix="/users", tags=["follows"])


@router.post("/{user_id}/follow", status_code=204)
def follow_user(user_id: str, db: Session = Depends(get_db), me=Depends(get_current_user)):
  if str(me.id) == user_id:
    raise HTTPException(status_code=400, detail="não pode se seguir")
  target = db.query(User).filter(cast(User.id, String) == user_id).first()
  if not target:
    raise HTTPException(status_code=404, detail="usuário não encontrado")

  # cria relação (idempotente com merge)
  link = Follow(follower_id=me.id, followee_id=target.id)
  db.merge(link)
  db.commit()

  # registra atividade de amizade (opcional: só na 1ª vez)
  exists = db.query(Activity).filter(
      Activity.actor_id == me.id,
      Activity.verb == Verb.ADD_FRIEND,
      Activity.object_type == ObjType.FOLLOW,
      Activity.target_user_id == target.id
  ).first()
  if not exists:
    a = Activity(
        actor_id=me.id,
        verb=Verb.ADD_FRIEND,
        object_type=ObjType.FOLLOW,
        object_id=me.id,            # sintético; não é usado depois
        target_user_id=target.id
    )
    db.add(a)
    db.commit()
  return


@router.delete("/{user_id}/follow", status_code=204)
def unfollow_user(user_id: str, db: Session = Depends(get_db), me=Depends(get_current_user)):
  from sqlalchemy import and_
  # apaga follow se existir
  q = db.query(Follow).filter(
      and_(Follow.follower_id == me.id, cast(
          Follow.followee_id, String) == user_id)
  )
  if q.first() is None:
    raise HTTPException(status_code=404, detail="follow não existe")
  q.delete(synchronize_session=False)
  db.commit()
  return
