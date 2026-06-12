import pytest
from uuid import uuid4
from unittest.mock import patch
from src.models.order import Order, OrderItem
from src.database import SessionLocal


MOCK_B2B_PRODUCT = {
    "id": "product-1",
    "title": "iPhone 15",
    "status": "MODERATED",
    "deleted": False,
    "images": [],
    "characteristics": [],
    "skus": [
        {
            "id": "sku-1",
            "name": "256GB Black",
            "price": 12999000,
            "active_quantity": 10,
            "image": "/s3/iphone.jpg",
            "characteristics": []
        }
    ]
}


class TestOrdersView:

    def test_orders_list_returns_own_orders_paginated(self, client, valid_jwt_with_fixed_id, db_session):
        """Happy path: list own orders with pagination"""
        token, user_id = valid_jwt_with_fixed_id

        for i in range(3):
            order = Order(
                id=str(uuid4()),
                user_id=user_id,
                status="PAID",
                total_amount=10000 * (i + 1),
                idempotency_key=str(uuid4())
            )
            db_session.add(order)
        db_session.commit()

        response = client.get(
            "/api/v1/orders?limit=2&offset=0",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total_count"] == 3
        assert data["limit"] == 2

    def test_order_detail_shows_fixed_prices(self, client, valid_jwt_with_fixed_id, db_session):
        """unit_price in OrderItem is fixed, not from current SKU"""
        token, user_id = valid_jwt_with_fixed_id

        order = Order(
            id=str(uuid4()),
            user_id=user_id,
            status="PAID",
            total_amount=25998000,
            idempotency_key=str(uuid4())
        )
        db_session.add(order)
        db_session.flush()

        order_item = OrderItem(
            id=str(uuid4()),
            order_id=order.id,
            sku_id="sku-1",
            product_id="product-1",
            product_title="iPhone 15",
            sku_name="256GB Black",
            quantity=2,
            unit_price=12999000,
            line_total=25998000
        )
        db_session.add(order_item)
        db_session.commit()

        response = client.get(
            f"/api/v1/orders/{order.id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["unit_price"] == 12999000
        assert data["items"][0]["product_title"] == "iPhone 15"
        assert data["items"][0]["sku_name"] == "256GB Black"
        assert data["total_amount"] == 25998000

    def test_other_user_order_returns_404_not_403(self, client, valid_jwt_with_fixed_id, valid_jwt, db_session):
        """IDOR: чужой заказ → 404 (не 403)"""
        token, owner_id = valid_jwt_with_fixed_id

        order = Order(
            id=str(uuid4()),
            user_id=owner_id,
            status="PAID",
            total_amount=10000,
            idempotency_key=str(uuid4())
        )
        db_session.add(order)
        db_session.commit()

        other_token = valid_jwt

        response = client.get(
            f"/api/v1/orders/{order.id}",
            headers={"Authorization": f"Bearer {other_token}"}
        )

        assert response.status_code == 404

    def test_order_list_status_filter(self, client, valid_jwt_with_fixed_id, db_session):
        """Status filter works"""
        token, user_id = valid_jwt_with_fixed_id

        paid_order = Order(
            id=str(uuid4()),
            user_id=user_id,
            status="PAID",
            total_amount=10000,
            idempotency_key=str(uuid4())
        )
        delivered_order = Order(
            id=str(uuid4()),
            user_id=user_id,
            status="DELIVERED",
            total_amount=20000,
            idempotency_key=str(uuid4())
        )
        db_session.add_all([paid_order, delivered_order])
        db_session.commit()

        response = client.get(
            "/api/v1/orders?status=PAID",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "PAID"
