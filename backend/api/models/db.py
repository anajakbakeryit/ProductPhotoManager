"""
SQLAlchemy models for ProductPhotoManager.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, BigInteger,
    ForeignKey, JSON, Index, func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), default="")
    role = Column(String(20), default="user")  # admin | user
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    sessions = relationship("Session", back_populates="user")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    barcode = Column(String(128), unique=True, nullable=False, index=True)
    name = Column(String(255), default="")
    category = Column(String(255), default="")
    note = Column(Text, default="")
    photo_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    photos = relationship("Photo", back_populates="product")


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    barcode = Column(String(128), nullable=False, index=True)
    angle = Column(String(30), nullable=False)
    count = Column(Integer, nullable=False)
    original_key = Column(String(500), nullable=False)  # storage path
    filename = Column(String(255), nullable=False)

    # Processing status
    status = Column(String(20), default="uploaded")  # uploaded | processing | done | error
    has_cutout = Column(Boolean, default=False)
    has_watermark = Column(Boolean, default=False)
    has_wm_original = Column(Boolean, default=False)

    # Metadata
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(BigInteger)
    tags = Column(JSON, default=[])

    # Relations
    session_id = Column(Integer, ForeignKey("sessions.id"))
    uploaded_by = Column(Integer, ForeignKey("users.id"))

    # Soft delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())

    product = relationship("Product", back_populates="photos")
    session = relationship("Session", back_populates="photos")
    activity_logs = relationship("ActivityLog", back_populates="photo")

    __table_args__ = (
        Index("idx_photos_barcode_angle", "barcode", "angle"),
        Index("idx_photos_status", "status"),
        Index("idx_photos_session", "session_id"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime, default=func.now())
    ended_at = Column(DateTime)
    photo_count = Column(Integer, default=0)
    barcode_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="sessions")
    photos = relationship("Photo", back_populates="session")


class AppSettings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    config = Column(JSON, nullable=False, default={})
    watermark_key = Column(String(500))
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"))


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True)
    photo_id = Column(Integer, ForeignKey("photos.id"))
    action = Column(String(50), nullable=False)
    message = Column(Text)
    status = Column(String(20))  # success | error | warning
    created_at = Column(DateTime, default=func.now(), index=True)

    photo = relationship("Photo", back_populates="activity_logs")
