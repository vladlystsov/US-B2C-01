import pytest
from uuid import uuid4
from unittest.mock import patch, MagicMock
from src.models.order import Order, OrderItem
from src.services.fulfill_service import FulfillService
from src.database import SessionLocal


class TestFulfill:

    def test_delivered_status_triggers_fulfill_to_b2b(self, client, db_session, valid_jwt_with_fixed_id):
        """Happy path: DELIVERED → fulfill to B2B"""
        token, user_id = valid_jwt_with_fixed_id

        order = Order(
            id=str(uuid4()),
            user_id=user_id,
            status="DELIVERED",
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
            quantity=2,
            unit_price=10000,
            line_total=20000
        )
        db_session.add(order_item)
        db_session.commit()

        with patch('src.services.fulfill_service.httpx.Client') as MockClient:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            service = FulfillService(db_session)
            result = service.trigger_fulfill(str(order.id))

        assert result["status"] == "fulfilled"

    def test_fulfill_failure_retried_asynchronously(self, client, db_session, valid_jwt_with_fixed_id):
        """B2B fails → retry_needed"""
        token, user_id = valid_jwt_with_fixed_id

        order = Order(
            id=str(uuid4()),
            user_id=user_id,
            status="DELIVERED",
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

        with patch('src.services.fulfill_service.httpx.Client') as MockClient:
            import httpx
            mock_client = MagicMock()
            mock_client.post.side_effect = httpx.RequestError("Connection refused")
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            service = FulfillService(db_session)
            result = service.trigger_fulfill(str(order.id))

        assert result["status"] == "retry_needed"
        assert "error" in result

    def test_repeated_fulfill_idempotent(self, client, db_session, valid_jwt_with_fixed_id):
        """Repeated fulfill with same order_id → 200"""
        token, user_id = valid_jwt_with_fixed_id

        order = Order(
            id=str(uuid4()),
            user_id=user_id,
            status="DELIVERED",
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

        with patch('src.services.fulfill_service.httpx.Client') as MockClient:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            MockClient.return_value = mock_client

            service = FulfillService(db_session)

            result1 = service.trigger_fulfill(str(order.id))
            assert result1["status"] == "fulfilled"

            result2 = service.trigger_fulfill(str(order.id))
            assert result2["status"] == "fulfilled"
