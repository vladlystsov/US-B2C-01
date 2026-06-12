from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.sql import func
from src.database import Base


class Banner(Base):
    __tablename__ = "banners"

    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    image_url = Column(String(500), nullable=False)
    link = Column(String(500), nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    start_at = Column(DateTime(timezone=True), nullable=True)
    end_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BannerEvent(Base):
    __tablename__ = "banner_events"

    id = Column(String(36), primary_key=True)
    banner_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=True)
    event = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
