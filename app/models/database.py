import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index, JSON, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class User(Base):
    """User model - represents a registered player."""
    
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversations = relationship("Conversation", back_populates="user")


class InviteCode(Base):
    """InviteCode model - controls registration access."""
    
    __tablename__ = "invite_codes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False, index=True)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)
    used_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)


class Conversation(Base):
    """Conversation model - represents a chat session."""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False, default="default")
    # Changed user_id to be a Foreign Key
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    __table_args__ = (
        Index("idx_conversations_tenant_user", "tenant_id", "user_id"),
    )


class Message(Base):
    """Message model - represents a single message in a conversation."""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (Index("idx_messages_conversation", "conversation_id"),)


class GameState(Base):
    """Game state model - tracks player state for a conversation/game session."""

    __tablename__ = "game_states"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    current_location = Column(String(100), default="start")
    inventory = Column(JSON, default=list)
    visited_locations = Column(JSON, default=list)
    player_stats = Column(JSON, default=dict)
    flags = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversation = relationship("Conversation")

    __table_args__ = (Index("idx_game_states_conversation", "conversation_id"),)


class Location(Base):
    """Location model - represents a place in the game world."""

    __tablename__ = "locations"

    id = Column(String(36), primary_key=True)  # e.g. "start"
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    interactables = Column(JSON, default=list)
    npcs = Column(JSON, default=list)

    exits = relationship(
        "LocationExit",
        foreign_keys="LocationExit.source_id",
        back_populates="source_location",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class LocationExit(Base):
    """LocationExit model - represents a connection between locations."""

    __tablename__ = "location_exits"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(36), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(String(36), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    direction = Column(String(50), nullable=False)

    source_location = relationship("Location", foreign_keys=[source_id], back_populates="exits")
    target_location = relationship("Location", foreign_keys=[target_id])

    __table_args__ = (
        Index("idx_location_exits_source", "source_id"),
        Index("idx_location_exits_target", "target_id"),
    )
