from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.sql import func

from src.database import Base


class CartUnavailability(Base):
    """Human-readable B2B unavailability reason, separate from the issue enum."""

    __tablename__ = "cart_unavailability"

    cart_item_id = Column(String(36), ForeignKey("cart_items.id", ondelete="CASCADE"), primary_key=True)
    message = Column(String(2000), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
