from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Text, ForeignKey
from sqlalchemy.sql import func
from src.database import Base


class Collection(Base):
    __tablename__ = "collections"

    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cover_image_url = Column(String(500), nullable=True)
    target_url = Column(String(500), nullable=True)
    priority = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    start_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CollectionProduct(Base):
    __tablename__ = "collection_products"

    collection_id = Column(String(36), ForeignKey("collections.id"), primary_key=True)
    product_id = Column(String(36), primary_key=True)
    ordering = Column(Integer, nullable=False, default=0)
