from types import SimpleNamespace

from src.config import settings
from src.models.cart import CartItem
from src.models.cart_unavailability import CartUnavailability
from src.models.price_drop_notification import PriceDropNotification
from src.models.subscription import ProductSubscription
from src.services import order_service
from src.services.b2b_client import b2b_client
from src.services.cart_service import CartService

USER_ID = "123e4567-e89b-12d3-a456-426614174000"
PRODUCT_ID = "00000000-0000-0000-0000-000000000001"
SKU_ID = "00000000-0000-0000-0000-000000000010"
PRICE_PRODUCT_ID = "00000000-0000-0000-0000-000000000002"


def product():
    return {
        "id": PRODUCT_ID,
        "title": "Kettle",
        "slug": "kettle",
        "description": "Steel kettle",
        "status": "MODERATED",
        "category_id": "00000000-0000-0000-0000-000000000100",
        "characteristics": [{"name": "brand", "value": "Neo"}],
        "images": [{"url": "https://example.test/kettle.jpg", "ordering": 0}],
        "skus": [{"id": SKU_ID, "name": "Steel", "price": 5000, "active_quantity": 3}],
    }


class _Response:
    status_code = 200

    def json(self):
        return {}

    def raise_for_status(self):
        return None


class _Client:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def post(self, *_args, **_kwargs):
        return _Response()


def test_attribute_filter_is_forwarded_to_b2b(client, monkeypatch):
    captured = {}

    def fake_get_products(**kwargs):
        captured.update(kwargs)
        return {"items": [product()], "total_count": 1, "limit": 20, "offset": 0}

    monkeypatch.setattr(b2b_client, "get_products", fake_get_products)
    response = client.get("/api/v1/catalog/products?filter[brand]=Neo")

    assert response.status_code == 200
    assert captured["filters"] == {"brand": "Neo"}


def test_cart_rejects_unavailable_sku_before_persisting(client, db_session):
    response = client.post(
        "/api/v1/cart/items",
        headers={"X-Session-Id": "guest"},
        json={"sku_id": SKU_ID, "quantity": 1},
    )

    assert response.status_code == 502  # the public B2B catalog is unavailable in this isolated test
    assert response.json() == {"code": "B2B_UNAVAILABLE", "message": "B2B service unavailable"}
    assert db_session.query(CartItem).count() == 0


def test_product_event_marks_related_cart_rows_and_back_in_stock_clears_reason(client, db_session):
    item = CartItem(id="cart-event", user_id=USER_ID, session_id=None, sku_id=SKU_ID, product_id=PRODUCT_ID, quantity=1)
    db_session.add(item)
    db_session.commit()
    headers = {"X-Service-Key": settings.B2B_TO_B2C_KEY}

    blocked = client.post(
        "/api/v1/b2b/events",
        headers=headers,
        json={
            "event_type": "PRODUCT_BLOCKED",
            "idempotency_key": "00000000-0000-0000-0000-000000000701",
            "occurred_at": "2026-01-01T00:00:00Z",
            "payload": {"product_id": PRODUCT_ID, "reason": "PRODUCT_BLOCKED"},
        },
    )
    assert blocked.status_code == 202
    assert db_session.get(CartItem, "cart-event").unavailable_reason == "PRODUCT_BLOCKED"

    restored = client.post(
        "/api/v1/b2b/events",
        headers=headers,
        json={
            "event_type": "SKU_BACK_IN_STOCK",
            "idempotency_key": "00000000-0000-0000-0000-000000000702",
            "occurred_at": "2026-01-01T01:00:00Z",
            "payload": {"product_id": PRODUCT_ID, "sku_id": SKU_ID, "available_quantity": 3},
        },
    )
    assert restored.status_code == 202
    assert db_session.get(CartItem, "cart-event").unavailable_reason is None


def test_checkout_changed_body_with_same_idempotency_key_returns_409(client, valid_jwt_with_fixed_id, monkeypatch):
    token, _ = valid_jwt_with_fixed_id
    cart = {
        "items": [{"sku_id": SKU_ID, "product_id": PRODUCT_ID, "name": "Kettle", "sku_code": "STEEL", "quantity": 1, "unit_price": 5000, "available_quantity": 3, "is_available": True}],
        "items_count": 1,
        "subtotal": 5000,
        "is_valid": True,
    }
    monkeypatch.setattr(CartService, "get_cart", lambda *_args, **_kwargs: cart)
    monkeypatch.setattr(order_service.httpx, "Client", _Client)
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "00000000-0000-0000-0000-000000000703"}
    first = client.post("/api/v1/orders", headers=headers, json={"address_id": "00000000-0000-0000-0000-000000000401", "payment_method_id": "00000000-0000-0000-0000-000000000501"})
    second = client.post("/api/v1/orders", headers=headers, json={"address_id": "00000000-0000-0000-0000-000000000402", "payment_method_id": "00000000-0000-0000-0000-000000000501"})

    assert first.status_code == 201
    assert {"id", "country", "city", "street", "building", "created_at"}.issubset(first.json()["address"])
    assert {"id", "type", "created_at"}.issubset(first.json()["payment_method"])
    assert second.status_code == 409
    assert second.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_facets_enrich_short_catalog_items_through_public_batch(client, monkeypatch):
    calls = []
    short = {
        "id": PRODUCT_ID,
        "title": "Kettle",
        "slug": "kettle",
        "status": "MODERATED",
        "category_id": "00000000-0000-0000-0000-000000000100",
        "min_price": 5000,
        "cover_image": None,
        "created_at": "2026-01-01T00:00:00Z",
    }
    monkeypatch.setattr(
        b2b_client,
        "get_products",
        lambda **_kwargs: {"items": [short], "total_count": 1, "limit": 100, "offset": 0},
    )
    monkeypatch.setattr(
        b2b_client,
        "get_products_batch",
        lambda product_ids: calls.append(product_ids) or [product()],
    )

    response = client.get("/api/v1/catalog/facets")

    assert response.status_code == 200
    assert calls == [[PRODUCT_ID]]
    assert response.json()["facets"] == [{"name": "brand", "values": [{"value": "Neo", "count": 1}]}]


def test_repeated_attribute_filter_values_are_forwarded_to_b2b(client, monkeypatch):
    captured = {}

    def fake_get_products(**kwargs):
        captured.update(kwargs)
        return {"items": [product()], "total_count": 1, "limit": 20, "offset": 0}

    monkeypatch.setattr(b2b_client, "get_products", fake_get_products)
    response = client.get("/api/v1/catalog/products?filter[brand]=Neo&filter[brand]=Other")

    assert response.status_code == 200
    assert captured["filters"] == {"brand": ["Neo", "Other"]}


def test_price_changed_enqueues_price_drop_notifications(client, db_session):
    db_session.add(
        ProductSubscription(
            id="subscription-price-drop",
            user_id=USER_ID,
            product_id=PRICE_PRODUCT_ID,
            notify_on=["PRICE_DROP"],
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/b2b/events",
        headers={"X-Service-Key": settings.B2B_TO_B2C_KEY},
        json={
            "event_type": "PRICE_CHANGED",
            "idempotency_key": "00000000-0000-0000-0000-000000000704",
            "occurred_at": "2026-01-01T00:00:00Z",
            "payload": {"product_id": PRICE_PRODUCT_ID, "sku_id": SKU_ID, "old_price": 5000, "new_price": 4200},
        },
    )

    assert response.status_code == 202
    notification = db_session.query(PriceDropNotification).one()
    assert (notification.user_id, notification.product_id, notification.sku_id) == (USER_ID, PRICE_PRODUCT_ID, SKU_ID)
    assert (notification.old_price, notification.new_price) == (5000, 4200)


def test_cart_validate_returns_current_cart_and_issues(client, db_session, monkeypatch):
    db_session.add(CartItem(id="validate-item", user_id=None, session_id="guest-validate", sku_id=SKU_ID, product_id=PRODUCT_ID, quantity=1))
    db_session.commit()
    monkeypatch.setattr(b2b_client, "get_products_batch", lambda _product_ids: [product()])

    response = client.post("/api/v1/cart/validate", headers={"X-Session-Id": "guest-validate"})

    assert response.status_code == 200
    assert response.json()["is_valid"] is True
    assert response.json()["issues"] == []
    assert response.json()["cart"]["items"][0]["sku_id"] == SKU_ID


def test_similar_products_forwards_contract_limit_to_b2b(client, monkeypatch):
    captured = {}

    def fake_similar(product_id, limit):
        captured.update({"product_id": product_id, "limit": limit})
        return [product()]

    monkeypatch.setattr(b2b_client, "get_similar_products", fake_similar)
    response = client.get(f"/api/v1/catalog/products/{PRODUCT_ID}/similar?limit=50")

    assert response.status_code == 200
    assert captured == {"product_id": PRODUCT_ID, "limit": 50}


def test_catalog_uses_openapi_default_popularity_sort(client, monkeypatch):
    captured = {}

    def fake_get_products(**kwargs):
        captured.update(kwargs)
        return {"items": [], "total_count": 0, "limit": 20, "offset": 0}

    monkeypatch.setattr(b2b_client, "get_products", fake_get_products)
    response = client.get("/api/v1/catalog/products")

    assert response.status_code == 200
    assert captured["sort"] == "popularity"


def test_facets_collect_all_b2b_pages(client, monkeypatch):
    first_id = PRODUCT_ID
    second_id = "00000000-0000-0000-0000-000000000099"
    calls = []

    def fake_get_products(**kwargs):
        calls.append(kwargs)
        if kwargs["offset"] == 0:
            return {"items": [{"id": first_id}], "total_count": 2, "limit": 100, "offset": 0}
        return {"items": [{"id": second_id}], "total_count": 2, "limit": 100, "offset": 1}

    first_product = product()
    second_product = product() | {"id": second_id, "characteristics": [{"name": "brand", "value": "Other"}]}
    monkeypatch.setattr(b2b_client, "get_products", fake_get_products)
    monkeypatch.setattr(b2b_client, "get_products_batch", lambda ids: [first_product, second_product] if ids == [first_id, second_id] else [])

    response = client.get("/api/v1/catalog/facets")

    assert response.status_code == 200
    assert [call["offset"] for call in calls] == [0, 1]
    assert response.json()["facets"] == [{"name": "brand", "values": [{"value": "Neo", "count": 1}, {"value": "Other", "count": 1}]}]


class _UnavailableClient:
    def __enter__(self):
        raise RuntimeError("B2B unavailable")

    def __exit__(self, *_args):
        return False


def test_checkout_returns_503_when_b2b_reserve_is_unavailable(client, valid_jwt_with_fixed_id, monkeypatch):
    token, _ = valid_jwt_with_fixed_id
    cart = {
        "items": [{"sku_id": SKU_ID, "product_id": PRODUCT_ID, "name": "Kettle", "sku_code": "STEEL", "quantity": 1, "unit_price": 5000, "available_quantity": 3, "is_available": True}],
        "items_count": 1,
        "subtotal": 5000,
        "is_valid": True,
    }
    monkeypatch.setattr(CartService, "get_cart", lambda *_args, **_kwargs: cart)
    monkeypatch.setattr(order_service.httpx, "Client", _UnavailableClient)

    response = client.post(
        "/api/v1/orders",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "00000000-0000-0000-0000-000000000705"},
        json={"address_id": "00000000-0000-0000-0000-000000000401", "payment_method_id": "00000000-0000-0000-0000-000000000501"},
    )

    assert response.status_code == 503
    assert response.json() == {"code": "B2B_UNAVAILABLE", "message": "B2B service unavailable"}



def test_nested_b2c_attribute_filter_is_forwarded_as_b2b_filters(client, monkeypatch):
    captured = {}

    def fake_get_products(**kwargs):
        captured.update(kwargs)
        return {"items": [product()], "total_count": 1, "limit": 20, "offset": 0}

    monkeypatch.setattr(b2b_client, "get_products", fake_get_products)
    response = client.get("/api/v1/catalog/products?filter[attributes][brand]=Neo&filter[attributes][memory]=256")

    assert response.status_code == 200
    assert captured["filters"] == {"brand": "Neo", "memory": "256"}


def test_block_event_keeps_contract_issue_type_and_exposes_reason_as_message(client, db_session, monkeypatch):
    db_session.add(
        CartItem(
            id="cart-human-reason",
            user_id=None,
            session_id="guest-human-reason",
            sku_id=SKU_ID,
            product_id=PRODUCT_ID,
            quantity=1,
        )
    )
    db_session.commit()
    event_response = client.post(
        "/api/v1/b2b/events",
        headers={"X-Service-Key": settings.B2B_TO_B2C_KEY},
        json={
            "event_type": "PRODUCT_BLOCKED",
            "idempotency_key": "00000000-0000-0000-0000-000000000706",
            "occurred_at": "2026-01-01T00:00:00Z",
            "payload": {"product_id": PRODUCT_ID, "reason": "Product contains prohibited content"},
        },
    )
    assert event_response.status_code == 202
    stored = db_session.get(CartItem, "cart-human-reason")
    assert stored.unavailable_reason == "PRODUCT_BLOCKED"
    assert db_session.get(CartUnavailability, stored.id).message == "Product contains prohibited content"

    monkeypatch.setattr(b2b_client, "get_products_batch", lambda _product_ids: [])
    monkeypatch.setattr(b2b_client, "get_public_sku", lambda _sku_id: (_ for _ in ()).throw(RuntimeError("not public")))
    response = client.post("/api/v1/cart/validate", headers={"X-Session-Id": "guest-human-reason"})

    assert response.status_code == 200
    assert response.json()["issues"] == [
        {
            "sku_id": SKU_ID,
            "type": "PRODUCT_BLOCKED",
            "message": "Product contains prohibited content",
        }
    ]
