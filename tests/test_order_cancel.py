import pytest
from uuid import uuid4
from unittest.mock import patch, MagicMock
from src.models.order import Order, OrderItem
from src.database import SessionLocal


class TestOrderCancel:

    def test_cancel_paid_order_transitions_to_cancelled(self, client, valid_jwt_with_fixed_id, db_session):
        """Happy path: cancel PAID order → CANCELLED"""
        token, user_id = valid_jwt_with_fixed_id

        order = Order(
            id=str(uuid4()),
            user_id=user_id,
            status="PAID",
            total_amount=10000,
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
            sku_name="256GB",
            quantity=1,
            unit_price=10000,
            line_total=10000
        )
        db_session.add(order_item)
        db_session.commit()

        with patch('src.services.order_service.httpx.Client') as MockClient:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            response = client.post(
                f"/api/v1/orders/{order.id}/cancel",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CANCELLED"

    def test_unreserve_failure_transitions_to_cancel_pending(self, client, valid_jwt_with_fixed_id, db_session):
        """B2B unavailable → CANCEL_PENDING"""
        token, user_id = valid_jwt_with_fixed_id

        order = Order(
            id=str(uuid4()),
            user_id=user_id,
            status="PAID",
            total_amount=10000,
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
            sku_name="256GB",
            quantity=1,
            unit_price=10000,
            line_total=10000
        )
        db_session.add(order_item)
        db_session.commit()

        with patch('src.services.order_service.httpx.Client') as MockClient:
            import httpx
            mock_client = MagicMock()
            mock_client.post.side_effect = httpx.RequestError("Connection refused")
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            response = client.post(
                f"/api/v1/orders/{order.id}/cancel",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CANCEL_PENDING"

    def test_cancel_assembling_order_returns_409(self, client, valid_jwt_with_fixed_id, db_session):
        """ASSEMBLING order → 409 CANCEL_NOT_ALLOWED"""
        token, user_id = valid_jwt_with_fixed_id

        order = Order(
            id=str(uuid4()),
            user_id=user_id,
            status="ASSEMBLING",
            total_amount=10000,
            idempotency_key=str(uuid4())
        )
        db_session.add(order)
        db_session.commit()

        response = client.post(
            f"/api/v1/orders/{order.id}/cancel",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "CANCEL_NOT_ALLOWED"
        assert data["current_status"] == "ASSEMBLING"

    def test_cancel_other_user_order_returns_404(self, client, valid_jwt_with_fixed_id, valid_jwt, db_session):
        """IDOR: чужой заказ → 404"""
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

        response = client.post(
            f"/api/v1/orders/{order.id}/cancel",
            headers={"Authorization": f"Bearer {other_token}"}
        )

        assert response.status_code == 404
