from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from src.models.order import Order, OrderItem
from src.services.b2b_client import b2b_client
from src.services.cart_service import CartService


class OrderService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _request_fingerprint(request) -> str:
        payload = {
            "address_id": request.address_id,
            "payment_method_id": request.payment_method_id,
            "comment": request.comment,
            "items_snapshot": sorted(
                [item.model_dump() for item in (request.items_snapshot or [])],
                key=lambda item: item["sku_id"],
            ),
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _address_snapshot(address_id: str, created_at: datetime | None = None) -> str:
        """Persist the complete AddressResponse shape with the order snapshot.

        This service currently receives an address identifier from the buyer profile
        boundary. Keeping a complete snapshot shape prevents later order responses
        from degrading to only {id}; unavailable profile fields are explicit nulls.
        """
        snapshot = {
            "id": address_id,
            "country": "",
            "region": None,
            "city": "",
            "street": "",
            "building": "",
            "apartment": None,
            "postal_code": None,
            "recipient_name": None,
            "recipient_phone": None,
            "is_default": False,
            "comment": None,
            "created_at": (created_at or datetime.utcnow()).isoformat(),
        }
        return json.dumps(snapshot, ensure_ascii=False)

    @staticmethod
    def _address_response(stored_address: str | None, created_at: datetime | None) -> dict:
        defaults = {
            "id": stored_address or "",
            "country": "",
            "region": None,
            "city": "",
            "street": "",
            "building": "",
            "apartment": None,
            "postal_code": None,
            "recipient_name": None,
            "recipient_phone": None,
            "is_default": False,
            "comment": None,
            "created_at": str(created_at) if created_at else None,
        }
        if not stored_address:
            return defaults
        try:
            decoded = json.loads(stored_address)
        except (TypeError, json.JSONDecodeError):
            return defaults
        if not isinstance(decoded, dict):
            return defaults
        defaults.update(decoded)
        return defaults

    @staticmethod
    def _payment_method_snapshot(payment_method_id: str, created_at: datetime | None = None) -> str:
        """Persist the complete mock PaymentMethodResponse used at checkout."""
        return json.dumps(
            {
                "id": payment_method_id,
                "type": "CARD",
                "is_default": False,
                "created_at": (created_at or datetime.utcnow()).isoformat(),
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _payment_method_response(
        stored_payment_method: str | None,
        created_at: datetime | None,
        fallback_id: str | None = None,
    ) -> dict | None:
        if not stored_payment_method and not fallback_id:
            return None
        fallback = {
            "id": fallback_id or "",
            "type": "CARD",
            "is_default": False,
            "created_at": str(created_at) if created_at else None,
        }
        if not stored_payment_method:
            return fallback
        try:
            decoded = json.loads(stored_payment_method)
        except (TypeError, json.JSONDecodeError):
            return fallback
        if not isinstance(decoded, dict):
            return fallback
        fallback.update(decoded)
        return fallback

    def _same_request(self, existing: Order, user_id: str, request, fingerprint: str) -> bool:
        if existing.user_id != user_id:
            return False
        if existing.request_fingerprint:
            return existing.request_fingerprint == fingerprint
        # Backward-compatible check for orders created before request_fingerprint.
        if self._address_response(existing.delivery_address, existing.created_at).get("id") != request.address_id:
            return False
        existing_items = self.db.query(OrderItem).filter(OrderItem.order_id == existing.id).all()
        if request.items_snapshot is None:
            return True
        expected = sorted((item.sku_id, item.quantity, item.unit_price) for item in existing_items)
        received = sorted((item.sku_id, item.quantity, item.unit_price) for item in request.items_snapshot)
        return expected == received

    def create_order(self, user_id: str, request, idempotency_key: str) -> dict:
        fingerprint = self._request_fingerprint(request)
        existing = self.db.query(Order).filter(Order.idempotency_key == idempotency_key).first()
        if existing:
            if self._same_request(existing, user_id, request, fingerprint):
                return {"status": "existing", "order": self._format_order(existing)}
            return {
                "code": "IDEMPOTENCY_KEY_REUSED",
                "message": "Idempotency-Key was already used with a different request body",
            }

        cart = CartService(self.db).get_cart(user_id=user_id)
        cart_items = cart["items"]
        issues = []
        if not cart_items:
            issues.append({"sku_id": "", "type": "OUT_OF_STOCK", "message": "Cart is empty"})
        for item in cart_items:
            if not item["is_available"]:
                issues.append(
                    {
                        "sku_id": item["sku_id"],
                        "type": item.get("unavailable_reason") or "OUT_OF_STOCK",
                        "message": "SKU is no longer available",
                    }
                )

        if request.items_snapshot is not None:
            snapshot = {item.sku_id: (item.quantity, item.unit_price) for item in request.items_snapshot}
            actual = {item["sku_id"]: (item["quantity"], item["unit_price"]) for item in cart_items}
            if snapshot != actual:
                for sku_id in set(snapshot) | set(actual):
                    if snapshot.get(sku_id) != actual.get(sku_id):
                        issues.append(
                            {
                                "sku_id": sku_id,
                                "type": "PRICE_CHANGED",
                                "message": "Cart state differs from items_snapshot",
                            }
                        )

        if issues:
            return {"code": "CART_INVALID", "message": "Cart validation failed", "cart": cart, "issues": issues}

        order_id = str(uuid.uuid4())
        reserve_items = [{"sku_id": item["sku_id"], "quantity": item["quantity"]} for item in cart_items]
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{b2b_client.base_url}/api/v1/inventory/reserve",
                    json={"idempotency_key": idempotency_key, "order_id": order_id, "items": reserve_items},
                    headers=b2b_client.headers,
                    timeout=10.0,
                )
                if response.status_code == 409:
                    details = response.json()
                    return {
                        "code": "RESERVE_FAILED",
                        "message": "Не удалось зарезервировать товары",
                        "failed_items": details.get("failed_items") or details.get("details", {}).get("failed_items", []),
                    }
                response.raise_for_status()
        except Exception:
            return {"code": "B2B_UNAVAILABLE", "message": "B2B service unavailable"}

        subtotal = sum(item["unit_price"] * item["quantity"] for item in cart_items)
        created_at = datetime.utcnow()
        order = Order(
            id=order_id,
            user_id=user_id,
            status="PAID",
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            delivery_address=self._address_snapshot(request.address_id, created_at),
            payment_method_snapshot=self._payment_method_snapshot(request.payment_method_id, created_at),
            total_amount=subtotal,
            created_at=created_at,
        )
        self.db.add(order)
        order_items = []
        for cart_item in cart_items:
            order_item = OrderItem(
                id=str(uuid.uuid4()),
                order_id=order_id,
                sku_id=cart_item["sku_id"],
                product_id=cart_item["product_id"],
                product_title=cart_item["name"],
                sku_name=cart_item.get("sku_code") or "",
                quantity=cart_item["quantity"],
                unit_price=cart_item["unit_price"],
                line_total=cart_item["unit_price"] * cart_item["quantity"],
            )
            self.db.add(order_item)
            order_items.append(order_item)
        self.db.commit()
        return {
            "status": "created",
            "order": self._format_order(order, order_items, payment_method_id=request.payment_method_id, comment=request.comment),
        }

    def cancel_order(self, user_id: str, order_id: str, reason: str | None = None) -> dict:
        order = self.db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).with_for_update().first()
        if not order:
            return {"code": "ORDER_NOT_FOUND", "message": "Order not found"}
        # Актуальный канон разрешает покупателю отмену, пока заказ ещё не
        # доставлен: CREATED, PAID, ASSEMBLING и DELIVERING.
        if order.status not in ["CREATED", "PAID", "ASSEMBLING", "DELIVERING"]:
            return {
                "code": "CANCEL_NOT_ALLOWED",
                "message": f"Отмена невозможна: заказ в статусе {order.status}",
                "current_status": order.status,
            }

        items = self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        # Reserve the cancellation transition under a row lock before performing
        # the remote call. DELIVERED can therefore never race with an unreserve.
        order.status = "CANCEL_PENDING"
        self.db.commit()
        unreserve_items = [{"sku_id": item.sku_id, "quantity": item.quantity} for item in items]
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{b2b_client.base_url}/api/v1/inventory/unreserve",
                    json={"order_id": order_id, "items": unreserve_items},
                    headers=b2b_client.headers,
                    timeout=10.0,
                )
                response.raise_for_status()
        except Exception:
            return {"status": "pending", "order": self._format_order(order, items, cancel_reason=reason)}

        locked = self.db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).with_for_update().first()
        if locked and locked.status == "CANCEL_PENDING":
            locked.status = "CANCELLED"
            self.db.commit()
        return {"status": "cancelled", "order": self._format_order(order, items, cancel_reason=reason)}

    def get_order(self, user_id: str, order_id: str) -> dict | None:
        order = self.db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
        return self._format_order(order) if order else None

    def get_orders(self, user_id: str, limit: int = 20, offset: int = 0, status: str | None = None) -> dict:
        query = self.db.query(Order).filter(Order.user_id == user_id)
        if status:
            query = query.filter(Order.status == status)
        total = query.count()
        orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
        return {
            "items": [self._format_order(order) for order in orders],
            "total_count": total,
            "limit": limit,
            "offset": offset,
        }

    def set_order_status(self, user_id: str, order_id: str, status: str) -> dict | None:
        order = self.db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).with_for_update().first()
        if not order:
            return None
        previous = order.status
        if status == "DELIVERED":
            if previous == "DELIVERED":
                return self._format_order(order)
            if previous != "DELIVERING":
                return {
                    "code": "INVALID_STATUS_TRANSITION",
                    "message": f"Cannot transition to DELIVERED from {previous}",
                    "current_status": previous,
                }
        order.status = status
        self.db.commit()
        # The model's after_commit hook triggers fulfill exactly once after a valid
        # DELIVERING → DELIVERED transition; no second synchronous call is made.
        return self._format_order(order)

    def _format_order(
        self,
        order: Order,
        items: list[OrderItem] | None = None,
        payment_method_id: str | None = None,
        comment: str | None = None,
        cancel_reason: str | None = None,
    ) -> dict:
        if items is None:
            items = self.db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        formatted_items = [
            {
                "sku_id": item.sku_id,
                "product_id": item.product_id,
                "name": item.product_title,
                "sku_code": item.sku_name or None,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
                "image_url": None,
            }
            for item in items
        ]
        subtotal = sum(item["line_total"] for item in formatted_items)
        created_at = str(order.created_at) if order.created_at else None
        return {
            "id": order.id,
            "buyer_id": order.user_id,
            "status": order.status,
            "status_history": [{"status": "CREATED", "changed_at": created_at}, {"status": order.status, "changed_at": str(order.updated_at) if order.updated_at else created_at}],
            "items": formatted_items,
            "subtotal": subtotal,
            "delivery_cost": 0,
            "total": order.total_amount if order.total_amount is not None else subtotal,
            "address": self._address_response(order.delivery_address, order.created_at),
            "payment_method": self._payment_method_response(
                order.payment_method_snapshot,
                order.created_at,
                fallback_id=payment_method_id,
            ),
            "comment": comment,
            "cancel_reason": cancel_reason,
            "created_at": created_at,
            "paid_at": created_at if order.status in {"PAID", "ASSEMBLING", "DELIVERING", "DELIVERED"} else None,
            "delivered_at": str(order.updated_at) if order.status == "DELIVERED" and order.updated_at else None,
        }
