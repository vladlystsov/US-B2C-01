from sqlalchemy.orm import Session
from src.models.favorite import Favorite
from src.services.b2b_client import b2b_client
import uuid
import httpx


class FavoritesService:
    def __init__(self, db: Session):
        self.db = db

    def add_favorite(self, user_id: str, product_id: str) -> dict:
        existing = self.db.query(Favorite).filter(
            Favorite.user_id == user_id,
            Favorite.product_id == product_id
        ).first()

        if existing:
            return {"product_id": product_id, "added_at": str(existing.added_at), "status": "exists"}

        fav = Favorite(
            id=str(uuid.uuid4()),
            user_id=user_id,
            product_id=product_id
        )
        self.db.add(fav)
        self.db.commit()

        return {"product_id": product_id, "added_at": str(fav.added_at), "status": "created"}

    def remove_favorite(self, user_id: str, product_id: str) -> bool:
        fav = self.db.query(Favorite).filter(
            Favorite.user_id == user_id,
            Favorite.product_id == product_id
        ).first()

        if fav:
            self.db.delete(fav)
            self.db.commit()
            return True

        return False

    def get_favorites(self, user_id: str, limit: int = 20, offset: int = 0) -> dict:
        query = self.db.query(Favorite).filter(Favorite.user_id == user_id)
        total = query.count()

        favorites = query.order_by(Favorite.added_at.desc()).offset(offset).limit(limit).all()

        if not favorites:
            return {"items": [], "total_count": total}

        product_ids = [fav.product_id for fav in favorites]

        try:
            b2b_data = b2b_client.get_products(limit=100, offset=0, ids=",".join(product_ids))
            b2b_products = {p["id"]: p for p in b2b_data.get("items", [])}
        except Exception:
            b2b_products = {}

        items = []
        for fav in favorites:
            product = b2b_products.get(fav.product_id)
            if product:
                skus = product.get("skus", [])
                min_price = min((s.get("price", 0) for s in skus if s.get("active_quantity", 0) > 0), default=0)
                in_stock = any(s.get("active_quantity", 0) > 0 for s in skus)
                image = None
                for s in skus:
                    if s.get("image"):
                        image = s["image"]
                        break
                if not image and product.get("images"):
                    image = product["images"][0].get("url") if isinstance(product["images"][0], dict) else product["images"][0]

                items.append({
                    "id": product.get("id"),
                    "title": product.get("title"),
                    "image": image,
                    "price": min_price,
                    "in_stock": in_stock,
                    "is_in_cart": False,
                    "added_at": str(fav.added_at)
                })

        return {"items": items, "total_count": total}
