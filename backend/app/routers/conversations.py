# backend/app/routers/conversations.py
from uuid import UUID  # <-- importe isto
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Conversation, ConversationParticipant, Message
from ..schemas import ConversationCreate, ConversationOut, MessageIn, MessageOut

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationOut)
def start_conversation(payload: ConversationCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
  if payload.other_user_id == user.id:
    raise HTTPException(
        status_code=400, detail="não pode iniciar conversa consigo mesmo")
  c = Conversation(is_group=False)
  db.add(c)
  db.flush()
  db.add_all([
      ConversationParticipant(conversation_id=c.id, user_id=user.id),
      ConversationParticipant(conversation_id=c.id,
                              user_id=payload.other_user_id),
  ])
  db.commit()
  db.refresh(c)
  return c


@router.get("", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db), user: UUID = Depends(get_current_user)):
  return db.query(Conversation)\
      .join(ConversationParticipant, ConversationParticipant.conversation_id == Conversation.id)\
      .filter(ConversationParticipant.user_id == user.id)\
      .order_by(Conversation.created_at.desc()).all()


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(
    conversation_id: UUID,  # <-- UUID aqui
    limit: int = 50,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
  # membership check correto (UUID == UUID)
  member = db.query(ConversationParticipant).filter(
      ConversationParticipant.conversation_id == conversation_id,
      ConversationParticipant.user_id == user.id
  ).first()
  if not member:
    raise HTTPException(status_code=403, detail="sem acesso")

  return db.query(Message).filter(
      Message.conversation_id == conversation_id
  ).order_by(Message.created_at.asc()).limit(limit).all()


@router.post("/{conversation_id}/messages", response_model=MessageOut)
def send_message(
    conversation_id: UUID,  # <-- UUID aqui
    payload: MessageIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
  member = db.query(ConversationParticipant).filter(
      ConversationParticipant.conversation_id == conversation_id,
      ConversationParticipant.user_id == user.id
  ).first()
  if not member:
    raise HTTPException(status_code=403, detail="sem acesso")

  m = Message(conversation_id=conversation_id,
              sender_id=user.id, content=payload.content)
  db.add(m)
  db.commit()
  db.refresh(m)
  return m
