from sqlalchemy.orm import Session
from .models import Activity, Verb, ObjType


def create_activity(db: Session, actor_id, verb: Verb, object_type: ObjType, object_id, target_user_id=None):
  a = Activity(actor_id=actor_id, verb=verb, object_type=object_type,
               object_id=object_id, target_user_id=target_user_id)
  db.add(a)
  db.commit()
  db.refresh(a)
  return a
