from datetime import date

from src.config import settings
from src.models.banner import Banner
from src.models.cart import CartItem
from src.models.collection import Collection, CollectionProduct
from src.services.b2b_client import b2b_client

PRODUCT_ID = "00000000-0000-0000-0000-000000000001"
SKU_ID = "00000000-0000-0000-0000-000000000010"
USER_ID = "123e4567-e89b-12d3-a456-426614174000"


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def product():
    return {
        "id": PRODUCT_ID, "title": "Kettle", "slug": "kettle", "status": "MODERATED",
        "images": [{"id": "image", "url": "https://example.test/kettle.jpg", "ordering": 0}],
        "skus": [{"id": SKU_ID, "name": "Steel", "price": 5000, "active_quantity": 5}],
    }


def test_favorites_use_put_204_and_list_contract_cards(client, valid_jwt_with_fixed_id, monkeypatch):
    token, _ = valid_jwt_with_fixed_id
    headers = auth_header(token)
    added = client.put(f"/api/v1/favorites/{PRODUCT_ID}", headers=headers)
    repeated = client.put(f"/api/v1/favorites/{PRODUCT_ID}", headers=headers)
    assert added.status_code == repeated.status_code == 204
    monkeypatch.setattr(b2b_client, "get_products_batch", lambda _ids: [product()])
    listed = client.get("/api/v1/favorites", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["items"][0]["name"] == "Kettle"


def test_subscriptions_accept_events_and_return_204(client, valid_jwt_with_fixed_id, monkeypatch):
    token, _ = valid_jwt_with_fixed_id
    monkeypatch.setattr(b2b_client, "get_product_by_id", lambda _id: product())
    headers = auth_header(token)
    response = client.post(f"/api/v1/favorites/{PRODUCT_ID}/subscribe", json={"events": ["BACK_IN_STOCK", "PRICE_DROP"]}, headers=headers)
    assert response.status_code == 204
    duplicate = client.post(f"/api/v1/favorites/{PRODUCT_ID}/subscribe", json={"events": ["BACK_IN_STOCK"]}, headers=headers)
    assert duplicate.status_code == 409


def test_cart_patch_delete_and_merge_return_cart_response(client, db_session, valid_jwt_with_fixed_id, monkeypatch):
    token, _ = valid_jwt_with_fixed_id
    monkeypatch.setattr(b2b_client, "get_products", lambda **_: {"items": [product()]})
    monkeypatch.setattr(b2b_client, "get_products_batch", lambda _product_ids: [product()])
    monkeypatch.setattr(
        b2b_client,
        "get_public_sku",
        lambda _sku_id: {**product()["skus"][0], "product_id": PRODUCT_ID},
    )
    session = "00000000-0000-0000-0000-000000000222"
    added = client.post("/api/v1/cart/items", headers={"X-Session-Id": session}, json={"sku_id": SKU_ID, "quantity": 2})
    assert added.status_code == 200 and added.json()["subtotal"] == 10000
    updated = client.patch(f"/api/v1/cart/items/{SKU_ID}", headers={"X-Session-Id": session}, json={"quantity": 3})
    assert updated.status_code == 200 and updated.json()["items_count"] == 3
    deleted = client.delete(f"/api/v1/cart/items/{SKU_ID}", headers={"X-Session-Id": session})
    assert deleted.status_code == 200 and deleted.json()["items"] == []

    client.post("/api/v1/cart/items", headers={"X-Session-Id": session}, json={"sku_id": SKU_ID, "quantity": 2})
    merged = client.post("/api/v1/cart/merge", headers={"X-Session-Id": session, **auth_header(token)})
    assert merged.status_code == 200 and merged.json()["items_count"] == 2


def test_banners_and_collections_use_catalog_paths_and_plain_arrays(client, db_session, monkeypatch):
    db_session.add(Banner(id="banner", title="Sale", image_url="https://example.test/banner.jpg", link="https://example.test/sale", priority=1, is_active=True))
    collection = Collection(id="collection", title="Weekly", description="Top picks", is_active=True, priority=1, start_date=date.today())
    db_session.add(collection)
    db_session.add(CollectionProduct(collection_id="collection", product_id=PRODUCT_ID, ordering=0))
    db_session.commit()
    monkeypatch.setattr(b2b_client, "get_products_batch", lambda _ids: [product()])
    banners = client.get("/api/v1/catalog/banners")
    collections = client.get("/api/v1/catalog/collections")
    assert banners.status_code == 200 and isinstance(banners.json(), list) and banners.json()[0]["ordering"] == 1
    assert collections.status_code == 200 and collections.json()[0]["name"] == "Weekly"
    assert collections.json()[0]["products"][0]["min_price"] == 5000
