from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from src.database import Base


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    product_id = Column(String(36), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
