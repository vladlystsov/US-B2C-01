import pytest
from uuid import uuid4
from datetime import datetime, timezone
from src.models.cart import CartItem
from src.config import settings


class TestProductEvents:

    def test_product_blocked_marks_cart_items_unavailable(self, client, db_session, valid_jwt_with_fixed_id):
        """PRODUCT_BLOCKED → cart_items get unavailable_reason"""
        token, user_id = valid_jwt_with_fixed_id

        cart_item = CartItem(
            id=str(uuid4()),
            user_id=user_id,
            sku_id="sku-1",
            quantity=2
        )
        db_session.add(cart_item)
        db_session.commit()

        response = client.post(
            "/api/v1/events/product",
            json={
                "idempotency_key": str(uuid4()),
                "event": "PRODUCT_BLOCKED",
                "product_id": str(uuid4()),
                "sku_ids": ["sku-1"],
                "reason": "Описание не соответствует товару",
                "date": datetime.now(timezone.utc).isoformat()
            },
            headers={"X-Service-Key": settings.B2B_SERVICE_KEY}
        )

        assert response.status_code == 200
        assert response.json()["accepted"] is True

        db_session.refresh(cart_item)
        assert cart_item.unavailable_reason == "PRODUCT_BLOCKED"

    def test_orders_not_affected_by_product_blocked(self, client, db_session, valid_jwt_with_fixed_id):
        """Orders not affected by PRODUCT_BLOCKED"""
        from src.models.order import Order

        token, user_id = valid_jwt_with_fixed_id

        order = Order(
            id=str(uuid4()),
            user_id=user_id,
            status="PAID",
            total_amount=10000,
            idempotency_key=str(uuid4())
        )
        db_session.add(order)
        db_session.commit()

        response = client.post(
            "/api/v1/events/product",
            json={
                "idempotency_key": str(uuid4()),
                "event": "PRODUCT_BLOCKED",
                "product_id": str(uuid4()),
                "sku_ids": ["sku-1"],
                "date": datetime.now(timezone.utc).isoformat()
            },
            headers={"X-Service-Key": settings.B2B_SERVICE_KEY}
        )

        assert response.status_code == 200

        db_session.refresh(order)
        assert order.status == "PAID"

    def test_idempotent_event_no_side_effects(self, client, db_session, valid_jwt_with_fixed_id):
        """Duplicate event → 200, no changes"""
        token, user_id = valid_jwt_with_fixed_id

        cart_item = CartItem(
            id=str(uuid4()),
            user_id=user_id,
            sku_id="sku-1",
            quantity=2
        )
        db_session.add(cart_item)
        db_session.commit()

        idempotency_key = str(uuid4())

        response1 = client.post(
            "/api/v1/events/product",
            json={
                "idempotency_key": idempotency_key,
                "event": "PRODUCT_BLOCKED",
                "product_id": str(uuid4()),
                "sku_ids": ["sku-1"],
                "date": datetime.now(timezone.utc).isoformat()
            },
            headers={"X-Service-Key": settings.B2B_SERVICE_KEY}
        )
        assert response1.status_code == 200

        response2 = client.post(
            "/api/v1/events/product",
            json={
                "idempotency_key": idempotency_key,
                "event": "PRODUCT_DELETED",
                "product_id": str(uuid4()),
                "sku_ids": ["sku-1"],
                "date": datetime.now(timezone.utc).isoformat()
            },
            headers={"X-Service-Key": settings.B2B_SERVICE_KEY}
        )
        assert response2.status_code == 200
        assert response2.json()["accepted"] is True

    def test_missing_service_key_returns_401(self, client):
        """No X-Service-Key → 401"""
        response = client.post(
            "/api/v1/events/product",
            json={
                "idempotency_key": str(uuid4()),
                "event": "PRODUCT_BLOCKED",
                "product_id": str(uuid4()),
                "sku_ids": ["sku-1"],
                "date": datetime.now(timezone.utc).isoformat()
            }
        )
        assert response.status_code == 401

    def test_product_deleted_marks_cart_items(self, client, db_session, valid_jwt_with_fixed_id):
        """PRODUCT_DELETED → unavailable_reason = PRODUCT_DELETED"""
        token, user_id = valid_jwt_with_fixed_id

        cart_item = CartItem(
            id=str(uuid4()),
            user_id=user_id,
            sku_id="sku-2",
            quantity=1
        )
        db_session.add(cart_item)
        db_session.commit()

        response = client.post(
            "/api/v1/events/product",
            json={
                "idempotency_key": str(uuid4()),
                "event": "PRODUCT_DELETED",
                "product_id": str(uuid4()),
                "sku_ids": ["sku-2"],
                "date": datetime.now(timezone.utc).isoformat()
            },
            headers={"X-Service-Key": settings.B2B_SERVICE_KEY}
        )

        assert response.status_code == 200
        db_session.refresh(cart_item)
        assert cart_item.unavailable_reason == "PRODUCT_DELETED"
