from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserCreate(BaseModel):
  username: str
  email: EmailStr
  password: str


class TokenOut(BaseModel):
  access_token: str
  token_type: str = "bearer"


class RecordCreate(BaseModel):
  matrix_code: str
  title: str
  artist: str
  year: Optional[int] = None
  genre: Optional[str] = None
  label: Optional[str] = None


class RecordOut(BaseModel):
  id: UUID
  matrix_code: str
  title: str
  artist: str
  year: Optional[int] = None
  genre: Optional[str] = None
  label: Optional[str] = None
  created_by: Optional[UUID] = None
  created_at: Optional[datetime] = None
  model_config = ConfigDict(from_attributes=True)


class CommentIn(BaseModel):
  content: str


class CommentOut(BaseModel):
  id: UUID
  user_id: UUID
  record_id: UUID
  content: str
  created_at: datetime
  model_config = ConfigDict(from_attributes=True)


class ActivityCommentIn(BaseModel):
  content: str


class ActivityCommentOut(BaseModel):
  id: UUID
  activity_id: UUID
  user_id: UUID
  content: str
  created_at: datetime
  model_config = ConfigDict(from_attributes=True)


class FavoriteUpdate(BaseModel):
  is_favorite: bool


class ReviewIn(BaseModel):
  record_id: UUID
  rating: int
  comment: Optional[str] = None


class ReviewOut(BaseModel):
  id: UUID
  user_id: UUID
  record_id: UUID
  rating: int
  comment: Optional[str] = None
  created_at: datetime
  model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
  other_user_id: UUID


class ConversationOut(BaseModel):
  id: UUID
  is_group: bool
  created_at: datetime
  model_config = ConfigDict(from_attributes=True)


class MessageIn(BaseModel):
  content: str


class MessageOut(BaseModel):
  id: UUID
  conversation_id: UUID
  sender_id: Optional[UUID]
  content: str
  created_at: datetime
  model_config = ConfigDict(from_attributes=True)
