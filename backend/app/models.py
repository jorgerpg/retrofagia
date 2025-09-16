from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, DateTime, UniqueConstraint, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .db import Base


class Verb(str, enum.Enum):
  ADD_RECORD = "ADD_RECORD"
  REVIEW = "REVIEW"
  COMMENT = "COMMENT"
  ADD_FRIEND = "ADD_FRIEND"


class ObjType(str, enum.Enum):
  RECORD = "RECORD"
  REVIEW = "REVIEW"
  COMMENT = "COMMENT"
  FOLLOW = "FOLLOW"


class User(Base):
  __tablename__ = "users"
  id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
  email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
  password_hash: Mapped[str] = mapped_column(String, nullable=False)
  name: Mapped[str | None] = mapped_column(String)
  bio: Mapped[str | None] = mapped_column(Text)
  avatar_url: Mapped[str | None] = mapped_column(String)
  created_at: Mapped[datetime] = mapped_column(
      DateTime, default=datetime.utcnow)


class Follow(Base):
  __tablename__ = "follows"
  follower_id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
  followee_id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
  created_at: Mapped[datetime] = mapped_column(
      DateTime, default=datetime.utcnow)


class Record(Base):
  __tablename__ = "records"
  id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  matrix_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
  title: Mapped[str] = mapped_column(String, nullable=False)
  artist: Mapped[str] = mapped_column(String, nullable=False)
  year: Mapped[int | None] = mapped_column(Integer)
  genre: Mapped[str | None] = mapped_column(String)
  label: Mapped[str | None] = mapped_column(String)
  created_by: Mapped[uuid.UUID | None] = mapped_column(
      UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
  created_at: Mapped[datetime] = mapped_column(
      DateTime, default=datetime.utcnow)


class UserCollection(Base):
  __tablename__ = "user_collection"
  user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(
      "users.id", ondelete="CASCADE"), primary_key=True)
  record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(
      "records.id", ondelete="CASCADE"), primary_key=True)
  is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
  added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Review(Base):
  __tablename__ = "reviews"
  id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  user_id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
  record_id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), ForeignKey("records.id", ondelete="CASCADE"))
  rating: Mapped[int] = mapped_column(Integer)
  comment: Mapped[str | None] = mapped_column(Text)
  created_at: Mapped[datetime] = mapped_column(
      DateTime, default=datetime.utcnow)
  __table_args__ = (UniqueConstraint(
      "user_id", "record_id", name="uq_review_user_record"),)


class Comment(Base):
  __tablename__ = "comments"
  id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  user_id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
  record_id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), ForeignKey("records.id", ondelete="CASCADE"))
  content: Mapped[str] = mapped_column(Text)
  created_at: Mapped[datetime] = mapped_column(
      DateTime, default=datetime.utcnow)


class Conversation(Base):
  __tablename__ = "conversations"
  id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  is_group: Mapped[bool] = mapped_column(Boolean, default=False)
  created_at: Mapped[datetime] = mapped_column(
      DateTime, default=datetime.utcnow)


class ConversationParticipant(Base):
  __tablename__ = "conversation_participants"
  conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(
      "conversations.id", ondelete="CASCADE"), primary_key=True)
  user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(
      "users.id", ondelete="CASCADE"), primary_key=True)


class Message(Base):
  __tablename__ = "messages"
  id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  conversation_id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"))
  sender_id: Mapped[uuid.UUID | None] = mapped_column(
      UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
  content: Mapped[str] = mapped_column(Text)
  created_at: Mapped[datetime] = mapped_column(
      DateTime, default=datetime.utcnow)


class Activity(Base):
  __tablename__ = "activity"
  id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  actor_id: Mapped[uuid.UUID | None] = mapped_column(
      UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
  verb: Mapped[Verb] = mapped_column(Enum(Verb), nullable=False)
  object_type: Mapped[ObjType] = mapped_column(Enum(ObjType), nullable=False)
  object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
  target_user_id: Mapped[uuid.UUID | None] = mapped_column(
      UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
  created_at: Mapped[datetime] = mapped_column(
      DateTime, default=datetime.utcnow)


class ActivityLike(Base):
  __tablename__ = "activity_likes"
  activity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(
      "activity.id", ondelete="CASCADE"), primary_key=True)
  user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(
      "users.id", ondelete="CASCADE"), primary_key=True)
  created_at: Mapped[datetime] = mapped_column(
      DateTime, default=datetime.utcnow)


class ActivityComment(Base):
  __tablename__ = "activity_comments"
  id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  activity_id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), ForeignKey("activity.id", ondelete="CASCADE"))
  user_id: Mapped[uuid.UUID] = mapped_column(
      UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
  content: Mapped[str] = mapped_column(Text)
  created_at: Mapped[datetime] = mapped_column(
      DateTime, default=datetime.utcnow)
