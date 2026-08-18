from datetime import date

from sqlalchemy.orm import Session

from src.models.collection import Collection, CollectionProduct
from src.services.b2b_client import b2b_client
from src.services.catalog_mapper import catalog_card


class CollectionService:
    def __init__(self, db: Session):
        self.db = db

    def _active_collections(self) -> list[Collection]:
        today = date.today()
        collections = self.db.query(Collection).filter(Collection.is_active.is_(True)).all()
        return sorted(
            [collection for collection in collections if not collection.start_date or collection.start_date <= today],
            key=lambda collection: collection.priority,
        )

    def _collection_payload(self, collection: Collection) -> dict:
        links = self.db.query(CollectionProduct).filter(CollectionProduct.collection_id == collection.id).order_by(CollectionProduct.ordering).all()
        product_ids = [link.product_id for link in links]
        products = b2b_client.get_products_batch(product_ids) if product_ids else []
        by_id = {str(product["id"]): product for product in products}
        available = [catalog_card(by_id[link.product_id]) for link in links if link.product_id in by_id]
        unavailable_ids = [link.product_id for link in links if link.product_id not in by_id]
        return {
            "id": collection.id,
            "name": collection.title,
            "description": collection.description,
            "products": available,
            "unavailable_ids": unavailable_ids,
        }

    def get_collections(self) -> list[dict]:
        return [self._collection_payload(collection) for collection in self._active_collections()]

    def get_collection_products(self, collection_id: str) -> dict | None:
        collection = self.db.query(Collection).filter(Collection.id == collection_id).first()
        if not collection:
            return None
        return self._collection_payload(collection)
