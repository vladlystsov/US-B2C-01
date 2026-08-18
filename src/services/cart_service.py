from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from src.models.cart import CartItem
from src.services.b2b_client import b2b_client
from src.services.catalog_mapper import cart_product_data


class CartService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _identity(user_id: str | None = None, session_id: str | None = None) -> dict | None:
        if user_id:
            return {"user_id": user_id, "session_id": None}
        if session_id:
            return {"user_id": None, "session_id": session_id}
        return None

    def _query_items(self, user_id: str | None = None, session_id: str | None = None):
        identity = self._identity(user_id, session_id)
        if not identity:
            return None
        return self.db.query(CartItem).filter(
            CartItem.user_id == identity["user_id"], CartItem.session_id == identity["session_id"]
        )

    def add_item(self, sku_id: str, quantity: int, user_id: str | None = None, session_id: str | None = None) -> dict:
        query = self._query_items(user_id, session_id)
        if query is None:
            return {"error": "MISSING_IDENTITY"}
        item = query.filter(CartItem.sku_id == sku_id).first()
        if item:
            item.quantity += quantity
            item.updated_at = datetime.utcnow()
        else:
            identity = self._identity(user_id, session_id)
            item = CartItem(id=str(uuid.uuid4()), sku_id=sku_id, quantity=quantity, **identity)
            self.db.add(item)
        self.db.commit()
        return self.get_cart(user_id, session_id)

    def update_item(self, sku_id: str, quantity: int, user_id: str | None = None, session_id: str | None = None) -> dict:
        query = self._query_items(user_id, session_id)
        if query is None:
            return {"error": "MISSING_IDENTITY"}
        item = query.filter(CartItem.sku_id == sku_id).first()
        if not item:
            return {"error": "NOT_FOUND"}
        item.quantity = quantity
        item.updated_at = datetime.utcnow()
        self.db.commit()
        return self.get_cart(user_id, session_id)

    def remove_item(self, sku_id: str, user_id: str | None = None, session_id: str | None = None) -> dict:
        query = self._query_items(user_id, session_id)
        if query is None:
            return {"error": "MISSING_IDENTITY"}
        item = query.filter(CartItem.sku_id == sku_id).first()
        if not item:
            return {"error": "NOT_FOUND"}
        self.db.delete(item)
        self.db.commit()
        return self.get_cart(user_id, session_id)

    def clear_cart(self, user_id: str | None = None, session_id: str | None = None) -> bool:
        query = self._query_items(user_id, session_id)
        if query is None:
            return False
        query.delete(synchronize_session=False)
        self.db.commit()
        return True

    def _products_by_sku(self, sku_ids: list[str]) -> dict[str, dict]:
        if not sku_ids:
            return {}
        # The B2B public batch endpoint returns an array. Product IDs are normally
        # available from the cart creation flow; legacy rows fall back to the same
        # compatibility proxy used by this MVP.
        try:
            data = b2b_client.get_products(limit=100, offset=0, ids=sku_ids)
            products = data.get("items", [])
        except Exception:
            products = []
        mapped: dict[str, dict] = {}
        for product in products:
            for sku in product.get("skus", []) or []:
                if sku.get("id") in sku_ids:
                    mapped[sku["id"]] = product

        # Legacy cart rows store only sku_id. Resolve missing entries through the
        # public SKU endpoint, then retrieve their public product by product_id.
        for sku_id in set(sku_ids) - set(mapped):
            try:
                sku = b2b_client.get_public_sku(sku_id)
                product_id = sku.get("product_id")
                if not product_id:
                    continue
                product = b2b_client.get_product_by_id(product_id)
                if product:
                    mapped[sku_id] = product
            except Exception:
                continue
        return mapped

    def get_cart(self, user_id: str | None = None, session_id: str | None = None) -> dict:
        query = self._query_items(user_id, session_id)
        if query is None:
            return {"items": [], "items_count": 0, "subtotal": 0, "is_valid": False}
        db_items = query.order_by(CartItem.created_at).all()
        if not db_items:
            return {"items": [], "items_count": 0, "subtotal": 0, "is_valid": True}

        try:
            by_sku = self._products_by_sku([item.sku_id for item in db_items])
        except Exception:
            by_sku = {}

        response_items = []
        subtotal = 0
        all_available = True
        for item in db_items:
            product = by_sku.get(item.sku_id)
            details = cart_product_data(product, item.sku_id) if product else None
            reason = item.unavailable_reason
            if not details:
                reason = reason or "PRODUCT_DELETED"
                response_items.append({
                    "sku_id": item.sku_id,
                    "product_id": "",
                    "name": "Unavailable product",
                    "quantity": item.quantity,
                    "unit_price": 0,
                    "line_total": 0,
                    "available_quantity": 0,
                    "is_available": False,
                    "unavailable_reason": reason,
                    "image": None,
                })
                all_available = False
                continue

            is_available = details["available_quantity"] >= item.quantity and not reason
            if not is_available:
                reason = reason or "OUT_OF_STOCK"
                all_available = False
            line_total = details["unit_price"] * item.quantity if is_available else 0
            subtotal += line_total
            response_items.append({
                **details,
                "quantity": item.quantity,
                "line_total": line_total,
                "is_available": is_available,
                "unavailable_reason": reason,
            })

        return {
            "items": response_items,
            "items_count": sum(item.quantity for item in db_items),
            "subtotal": subtotal,
            "is_valid": all_available,
        }

    def merge_guest_cart(self, user_id: str, session_id: str) -> dict:
        guest_items = self.db.query(CartItem).filter(CartItem.session_id == session_id, CartItem.user_id.is_(None)).all()
        for guest_item in guest_items:
            existing = self.db.query(CartItem).filter(CartItem.user_id == user_id, CartItem.sku_id == guest_item.sku_id).first()
            if existing:
                existing.quantity = max(existing.quantity, guest_item.quantity)
                self.db.delete(guest_item)
            else:
                guest_item.user_id = user_id
                guest_item.session_id = None
        self.db.commit()
        return self.get_cart(user_id=user_id)
