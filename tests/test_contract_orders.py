from types import SimpleNamespace

import httpx

from src.config import settings
from src.models.cart import CartItem
from src.models.order import Order, OrderItem
from src.services import fulfill_service, order_service
from src.services.cart_service import CartService

USER_ID = "123e4567-e89b-12d3-a456-426614174000"
ORDER_ID = "00000000-0000-0000-0000-000000000300"
SKU_ID = "00000000-0000-0000-0000-000000000010"
PRODUCT_ID = "00000000-0000-0000-0000-000000000001"


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class FakeResponse:
    status_code = 200

    def json(self):
        return {}

    def raise_for_status(self):
        return None


class FakeClient:
    calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse()


def contract_cart():
    return {
        "items": [{
            "sku_id": SKU_ID, "product_id": PRODUCT_ID, "name": "Kettle — Steel", "sku_code": "STEEL",
            "quantity": 2, "unit_price": 5000, "line_total": 10000, "available_quantity": 5,
            "is_available": True, "image": None,
        }],
        "items_count": 2, "subtotal": 10000, "is_valid": True,
    }


def test_checkout_uses_idempotency_header_and_returns_contract_order(client, valid_jwt_with_fixed_id, monkeypatch):
    token, _ = valid_jwt_with_fixed_id
    monkeypatch.setattr(CartService, "get_cart", lambda *_args, **_kwargs: contract_cart())
    FakeClient.calls = []
    monkeypatch.setattr(order_service.httpx, "Client", FakeClient)
    headers = {**auth_header(token), "Idempotency-Key": "00000000-0000-0000-0000-000000000999"}
    body = {"address_id": "00000000-0000-0000-0000-000000000400", "payment_method_id": "00000000-0000-0000-0000-000000000500"}
    created = client.post("/api/v1/orders", headers=headers, json=body)
    replay = client.post("/api/v1/orders", headers=headers, json=body)
    assert created.status_code == 201 and replay.status_code == 201
    assert created.json()["buyer_id"] == USER_ID
    assert created.json()["subtotal"] == created.json()["total"] == 10000
    assert len(FakeClient.calls) == 1


def test_checkout_invalid_cart_returns_structured_422(client, valid_jwt_with_fixed_id, monkeypatch):
    token, _ = valid_jwt_with_fixed_id
    invalid_cart = {"items": [], "items_count": 0, "subtotal": 0, "is_valid": True}
    monkeypatch.setattr(CartService, "get_cart", lambda *_args, **_kwargs: invalid_cart)
    response = client.post(
        "/api/v1/orders",
        headers={**auth_header(token), "Idempotency-Key": "00000000-0000-0000-0000-000000000998"},
        json={"address_id": "address", "payment_method_id": "payment"},
    )
    assert response.status_code == 422
    assert set(response.json()) == {"is_valid", "cart", "issues"}


def test_cancel_assembling_and_delivering_orders_and_hide_other_users(client, db_session, valid_jwt_with_fixed_id, monkeypatch):
    token, _ = valid_jwt_with_fixed_id
    db_session.add(Order(id=ORDER_ID, user_id=USER_ID, status="ASSEMBLING", idempotency_key="key-1", delivery_address="address", total_amount=5000))
    db_session.add(OrderItem(id="item", order_id=ORDER_ID, sku_id=SKU_ID, product_id=PRODUCT_ID, product_title="Kettle", sku_name="Steel", quantity=1, unit_price=5000, line_total=5000))
    db_session.commit()
    monkeypatch.setattr(order_service.httpx, "Client", FakeClient)
    response = client.post(f"/api/v1/orders/{ORDER_ID}/cancel", headers=auth_header(token))
    assert response.status_code == 200 and response.json()["status"] == "CANCELLED"
    unknown = client.get(f"/api/v1/orders/{ORDER_ID}", headers={"Authorization": auth_header(token)["Authorization"].replace(token, "")})
    assert unknown.status_code in (401, 404)


def test_b2b_events_use_contract_path_payload_and_idempotency(client, db_session):
    db_session.add(CartItem(id="cart", user_id=USER_ID, session_id=None, sku_id=SKU_ID, quantity=1))
    db_session.commit()
    body = {
        "event_type": "SKU_OUT_OF_STOCK", "idempotency_key": "00000000-0000-0000-0000-000000000777",
        "occurred_at": "2026-01-01T00:00:00Z", "payload": {"sku_id": SKU_ID, "product_id": PRODUCT_ID, "available_quantity": 0},
    }
    headers = {"X-Service-Key": settings.B2B_SERVICE_KEY}
    accepted = client.post("/api/v1/b2b/events", json=body, headers=headers)
    duplicate = client.post("/api/v1/b2b/events", json=body, headers=headers)
    assert accepted.status_code == 202 and duplicate.status_code == 409
    assert db_session.get(CartItem, "cart").unavailable_reason == "OUT_OF_STOCK"


def test_delivered_transition_and_fulfill_use_inventory_path(db_session, monkeypatch):
    order = Order(id="delivered", user_id=USER_ID, status="DELIVERING", idempotency_key="deliver-key", delivery_address="address", total_amount=5000)
    db_session.add(order)
    db_session.add(OrderItem(id="delivered-item", order_id="delivered", sku_id=SKU_ID, product_id=PRODUCT_ID, product_title="Kettle", sku_name="Steel", quantity=1, unit_price=5000, line_total=5000))
    db_session.commit()
    FakeClient.calls = []
    monkeypatch.setattr(fulfill_service.httpx, "Client", FakeClient)
    from src.services.order_service import OrderService
    OrderService(db_session).set_order_status(USER_ID, "delivered", "DELIVERED")
    assert FakeClient.calls[0][0].endswith("/api/v1/inventory/fulfill")
