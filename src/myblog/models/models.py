from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, Enum, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

Base = declarative_base()

# Define the Role Enum
class Role(enum.Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"

# Association table for Article-MediaFile relationship
card_media = Table(
    'card_media',
    Base.metadata,
    Column('card_id', Integer, ForeignKey('cards.id')),
    Column('media_id', Integer, ForeignKey('media_files.id'))
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    role = Column(Enum(Role), default=Role.VIEWER)
    cards = relationship("Card", back_populates="author")

class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author_id = Column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="cards")
    media_files = relationship("MediaFile", secondary=card_media, back_populates="cards")
    to_all = Column(Boolean, default=False)

class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    file_path = Column(String(255))
    file_type = Column(String(50))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    uploader_id = Column(Integer, ForeignKey("users.id"))
    uploader = relationship("User")
    cards = relationship("Card", secondary=card_media, back_populates="media_files")