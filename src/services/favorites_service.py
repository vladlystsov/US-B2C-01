import uuid

from sqlalchemy.orm import Session

from src.models.favorite import Favorite
from src.services.b2b_client import b2b_client
from src.services.catalog_mapper import catalog_card


class FavoritesService:
    def __init__(self, db: Session):
        self.db = db

    def add_favorite(self, user_id: str, product_id: str) -> dict:
        existing = self.db.query(Favorite).filter(Favorite.user_id == user_id, Favorite.product_id == product_id).first()
        if existing:
            return {"product_id": product_id, "status": "exists"}
        favorite = Favorite(id=str(uuid.uuid4()), user_id=user_id, product_id=product_id)
        self.db.add(favorite)
        self.db.commit()
        return {"product_id": product_id, "status": "created"}

    def remove_favorite(self, user_id: str, product_id: str) -> bool:
        favorite = self.db.query(Favorite).filter(Favorite.user_id == user_id, Favorite.product_id == product_id).first()
        if not favorite:
            return False
        self.db.delete(favorite)
        self.db.commit()
        return True

    def get_favorites(self, user_id: str, limit: int = 20, offset: int = 0) -> dict:
        query = self.db.query(Favorite).filter(Favorite.user_id == user_id)
        total = query.count()
        favorites = query.order_by(Favorite.added_at.desc()).offset(offset).limit(limit).all()
        if not favorites:
            return {"items": [], "total_count": total, "limit": limit, "offset": offset}

        product_ids = [favorite.product_id for favorite in favorites]
        products = b2b_client.get_products_batch(product_ids)
        by_id = {str(product["id"]): product for product in products}
        # Products omitted by B2B are blocked/deleted/non-public and must not leak into the buyer list.
        items = [catalog_card(by_id[favorite.product_id]) for favorite in favorites if favorite.product_id in by_id]
        return {"items": items, "total_count": total, "limit": limit, "offset": offset}
