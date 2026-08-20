from __future__ import annotations

import uuid
from datetime import datetime

import httpx
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

    @staticmethod
    def _sku_error(code: str, message: str) -> dict:
        return {"error": code, "code": code, "message": message}

    def _validate_sku(self, sku_id: str, requested_quantity: int) -> dict:
        """Validate SKU existence and current stock in B2B before persisting a cart row."""
        try:
            sku = b2b_client.get_public_sku(sku_id)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return self._sku_error("SKU_UNAVAILABLE", "SKU is unavailable")
            return self._sku_error("B2B_UNAVAILABLE", "B2B service unavailable")
        except Exception:
            return self._sku_error("B2B_UNAVAILABLE", "B2B service unavailable")

        available_quantity = sku.get("active_quantity", sku.get("available_quantity"))
        if available_quantity is None:
            return self._sku_error("SKU_UNAVAILABLE", "SKU is unavailable")
        if available_quantity < requested_quantity:
            return self._sku_error("SKU_UNAVAILABLE", "Requested quantity is unavailable")
        product_id = sku.get("product_id")
        if not product_id:
            return self._sku_error("SKU_UNAVAILABLE", "SKU has no public product")
        return {"sku": sku, "product_id": product_id}

    def add_item(self, sku_id: str, quantity: int, user_id: str | None = None, session_id: str | None = None) -> dict:
        query = self._query_items(user_id, session_id)
        if query is None:
            return self._sku_error("MISSING_IDENTITY", "Cart identity is required")
        item = query.filter(CartItem.sku_id == sku_id).first()
        requested_quantity = (item.quantity if item else 0) + quantity
        validated = self._validate_sku(sku_id, requested_quantity)
        if validated.get("error"):
            return validated

        if item:
            item.quantity = requested_quantity
            item.product_id = validated["product_id"]
            item.unavailable_reason = None
            item.updated_at = datetime.utcnow()
        else:
            identity = self._identity(user_id, session_id)
            item = CartItem(
                id=str(uuid.uuid4()),
                sku_id=sku_id,
                product_id=validated["product_id"],
                quantity=quantity,
                **identity,
            )
            self.db.add(item)
        self.db.commit()
        return self.get_cart(user_id, session_id)

    def update_item(self, sku_id: str, quantity: int, user_id: str | None = None, session_id: str | None = None) -> dict:
        query = self._query_items(user_id, session_id)
        if query is None:
            return self._sku_error("MISSING_IDENTITY", "Cart identity is required")
        item = query.filter(CartItem.sku_id == sku_id).first()
        if not item:
            return self._sku_error("NOT_FOUND", "Cart item not found")
        validated = self._validate_sku(sku_id, quantity)
        if validated.get("error"):
            return validated
        item.quantity = quantity
        item.product_id = validated["product_id"]
        item.unavailable_reason = None
        item.updated_at = datetime.utcnow()
        self.db.commit()
        return self.get_cart(user_id, session_id)

    def remove_item(self, sku_id: str, user_id: str | None = None, session_id: str | None = None) -> dict:
        query = self._query_items(user_id, session_id)
        if query is None:
            return self._sku_error("MISSING_IDENTITY", "Cart identity is required")
        item = query.filter(CartItem.sku_id == sku_id).first()
        if not item:
            return self._sku_error("NOT_FOUND", "Cart item not found")
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

    def _products_by_sku(self, items: list[CartItem]) -> dict[str, dict]:
        """Resolve cart rows through the B2B public batch contract.

        New rows persist product_id after SKU validation. Only legacy rows without
        it need an SKU-detail then product-detail fallback.
        """
        sku_ids = [item.sku_id for item in items]
        if not sku_ids:
            return {}
        product_ids = list({item.product_id for item in items if item.product_id})
        try:
            products = b2b_client.get_products_batch(product_ids) if product_ids else []
        except Exception:
            products = []

        mapped: dict[str, dict] = {}
        for product in products:
            for sku in product.get("skus", []) or []:
                if sku.get("id") in sku_ids:
                    mapped[sku["id"]] = product

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
            by_sku = self._products_by_sku(db_items)
        except Exception:
            by_sku = {}

        response_items = []
        subtotal = 0
        all_available = True
        stale_reasons_cleared = False
        for item in db_items:
            product = by_sku.get(item.sku_id)
            details = cart_product_data(product, item.sku_id) if product else None
            reason = item.unavailable_reason
            if not details:
                reason = reason or "PRODUCT_DELETED"
                response_items.append({
                    "sku_id": item.sku_id,
                    "product_id": item.product_id or "",
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

            # The public B2B response is authoritative. A returned SKU belongs to a
            # visible product, therefore an old event marker must not keep it stale.
            item.product_id = details["product_id"]
            reason = None
            if item.unavailable_reason is not None:
                item.unavailable_reason = None
                stale_reasons_cleared = True
            is_available = details["available_quantity"] >= item.quantity
            if not is_available:
                reason = "OUT_OF_STOCK"
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

        if stale_reasons_cleared:
            self.db.commit()
        return {
            "items": response_items,
            "items_count": sum(item.quantity for item in db_items),
            "subtotal": subtotal,
            "is_valid": all_available,
        }

    def validate_cart(self, user_id: str | None = None, session_id: str | None = None) -> dict:
        """Return checkout readiness and per-SKU issues from current B2B data."""
        cart = self.get_cart(user_id=user_id, session_id=session_id)
        issues: list[dict] = []
        if not cart["items"]:
            issues.append({"sku_id": "", "type": "OUT_OF_STOCK", "message": "Cart is empty"})
        for item in cart["items"]:
            if not item["is_available"]:
                issues.append(
                    {
                        "sku_id": item["sku_id"],
                        "type": item.get("unavailable_reason") or "OUT_OF_STOCK",
                        "message": "SKU is no longer available in the requested quantity",
                    }
                )
        return {"is_valid": not issues, "cart": cart, "issues": issues}

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
