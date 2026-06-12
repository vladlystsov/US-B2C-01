from sqlalchemy.orm import Session
from src.models.collection import Collection, CollectionProduct
from src.services.b2b_client import b2b_client
from datetime import date


class CollectionService:
    def __init__(self, db: Session):
        self.db = db

    def get_collections(self, limit: int = 10, offset: int = 0) -> dict:
        today = date.today()

        query = self.db.query(Collection).filter(
            Collection.is_active == True
        )

        all_collections = query.all()

        active = []
        for col in all_collections:
            if col.start_date and col.start_date > today:
                continue
            active.append(col)

        active.sort(key=lambda x: x.priority)
        total = len(active)
        paginated = active[offset:offset + limit]

        items = [{
            "id": col.id,
            "title": col.title,
            "description": col.description,
            "cover_image_url": col.cover_image_url,
            "target_url": col.target_url,
            "priority": col.priority
        } for col in paginated]

        return {"collections": items, "total_count": total}

    def get_collection_products(self, collection_id: str, limit: int = 20, offset: int = 0) -> dict | None:
        collection = self.db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            return None

        col_products = self.db.query(CollectionProduct).filter(
            CollectionProduct.collection_id == collection_id
        ).order_by(CollectionProduct.ordering).all()

        if not col_products:
            return {
                "collection_title": collection.title,
                "items": [],
                "unavailable_ids": [],
                "total_products": 0
            }

        product_ids = [cp.product_id for cp in col_products]

        try:
            b2b_data = b2b_client.get_products(limit=100, offset=0, ids=",".join(product_ids))
            b2b_products = {p["id"]: p for p in b2b_data.get("items", [])}
        except Exception:
            b2b_products = {}

        items = []
        unavailable_ids = []

        for cp in col_products:
            product = b2b_products.get(cp.product_id)
            if not product:
                unavailable_ids.append(cp.product_id)
                continue

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
                "is_in_cart": False
            })

        paginated_items = items[offset:offset + limit]

        return {
            "collection_title": collection.title,
            "items": paginated_items,
            "unavailable_ids": unavailable_ids,
            "total_products": len(items)
        }
