from sqlalchemy.orm import Session
from src.models.cart import CartItem
from src.services.b2b_client import b2b_client
import uuid
import httpx


class CartService:
    def __init__(self, db: Session):
        self.db = db

    def _get_identity(self, user_id: str = None, session_id: str = None):
        if user_id:
            return {"user_id": user_id, "session_id": None}
        if session_id:
            return {"user_id": None, "session_id": session_id}
        return None

    def add_item(self, sku_id: str, quantity: int, user_id: str = None, session_id: str = None) -> dict:
        identity = self._get_identity(user_id, session_id)
        if not identity:
            return {"error": "MISSING_IDENTITY"}

        query = self.db.query(CartItem).filter(
            CartItem.sku_id == sku_id,
            CartItem.user_id == identity["user_id"],
            CartItem.session_id == identity["session_id"]
        )

        existing = query.first()

        if existing:
            existing.quantity += quantity
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            return {"status": "updated", "item_id": existing.id, "quantity": existing.quantity}

        item = CartItem(
            id=str(uuid.uuid4()),
            user_id=identity["user_id"],
            session_id=identity["session_id"],
            sku_id=sku_id,
            quantity=quantity
        )
        self.db.add(item)
        self.db.commit()

        return {"status": "created", "item_id": item.id, "quantity": item.quantity}

    def update_item(self, item_id: str, quantity: int, user_id: str = None, session_id: str = None) -> dict:
        identity = self._get_identity(user_id, session_id)
        if not identity:
            return {"error": "MISSING_IDENTITY"}

        item = self.db.query(CartItem).filter(
            CartItem.id == item_id,
            CartItem.user_id == identity["user_id"],
            CartItem.session_id == identity["session_id"]
        ).first()

        if not item:
            return {"error": "NOT_FOUND"}

        item.quantity = quantity
        item.updated_at = datetime.utcnow()
        self.db.commit()

        return {"status": "updated", "item_id": item.id, "quantity": item.quantity}

    def remove_item(self, item_id: str, user_id: str = None, session_id: str = None) -> bool:
        identity = self._get_identity(user_id, session_id)
        if not identity:
            return False

        item = self.db.query(CartItem).filter(
            CartItem.id == item_id,
            CartItem.user_id == identity["user_id"],
            CartItem.session_id == identity["session_id"]
        ).first()

        if item:
            self.db.delete(item)
            self.db.commit()
            return True

        return False

    def clear_cart(self, user_id: str = None, session_id: str = None) -> bool:
        identity = self._get_identity(user_id, session_id)
        if not identity:
            return False

        items = self.db.query(CartItem).filter(
            CartItem.user_id == identity["user_id"],
            CartItem.session_id == identity["session_id"]
        ).all()

        for item in items:
            self.db.delete(item)

        self.db.commit()
        return True

    def get_cart(self, user_id: str = None, session_id: str = None) -> dict:
        identity = self._get_identity(user_id, session_id)
        if not identity:
            return {"items": [], "summary": {"total_amount": 0, "total_items": 0, "unavailable_count": 0, "checkout_ready": True}}

        items = self.db.query(CartItem).filter(
            CartItem.user_id == identity["user_id"],
            CartItem.session_id == identity["session_id"]
        ).all()

        if not items:
            return {"items": [], "summary": {"total_amount": 0, "total_items": 0, "unavailable_count": 0, "checkout_ready": True}}

        sku_ids = [item.sku_id for item in items]

        try:
            b2b_data = b2b_client.get_products(limit=100, offset=0, ids=",".join(sku_ids))
            b2b_products = {p["id"]: p for p in b2b_data.get("items", [])}
        except Exception:
            b2b_products = {}

        enriched_items = []
        total_amount = 0
        total_items = 0
        unavailable_count = 0

        for item in items:
            product = None
            sku_data = None

            for pid, pdata in b2b_products.items():
                for s in pdata.get("skus", []):
                    if s.get("id") == item.sku_id:
                        product = pdata
                        sku_data = s
                        break
                if product:
                    break

            if not product or not sku_data:
                enriched_items.append({
                    "id": item.id,
                    "sku_id": item.sku_id,
                    "quantity": item.quantity,
                    "available": False,
                    "unavailable_reason": "PRODUCT_DELETED"
                })
                unavailable_count += 1
                continue

            active_qty = sku_data.get("active_quantity", 0)
            available = active_qty >= item.quantity

            enriched_items.append({
                "id": item.id,
                "sku_id": item.sku_id,
                "quantity": item.quantity,
                "product_id": product.get("id"),
                "title": product.get("title"),
                "image": sku_data.get("image"),
                "price": sku_data.get("price", 0),
                "available": available,
                "unavailable_reason": "OUT_OF_STOCK" if not available else None
            })

            if available:
                total_amount += sku_data.get("price", 0) * item.quantity
                total_items += item.quantity
            else:
                unavailable_count += 1

        return {
            "items": enriched_items,
            "summary": {
                "total_amount": total_amount,
                "total_items": total_items,
                "unavailable_count": unavailable_count,
                "checkout_ready": unavailable_count == 0
            }
        }

    def merge_guest_cart(self, user_id: str, session_id: str) -> dict:
        guest_items = self.db.query(CartItem).filter(
            CartItem.session_id == session_id,
            CartItem.user_id == None
        ).all()

        for guest_item in guest_items:
            existing = self.db.query(CartItem).filter(
                CartItem.user_id == user_id,
                CartItem.sku_id == guest_item.sku_id
            ).first()

            if existing:
                existing.quantity = max(existing.quantity, guest_item.quantity)
                self.db.delete(guest_item)
            else:
                guest_item.user_id = user_id
                guest_item.session_id = None

        self.db.commit()
        return {"status": "merged"}


from datetime import datetime
