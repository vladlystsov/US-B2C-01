import pytest

from src.services.b2b_client import b2b_client

PRODUCT_ID = "00000000-0000-0000-0000-000000000001"
SKU_ID = "00000000-0000-0000-0000-000000000010"
CATEGORY_ID = "00000000-0000-0000-0000-000000000100"


def public_product(product_id=PRODUCT_ID, category_id=CATEGORY_ID):
    return {
        "id": product_id,
        "title": "Coffee maker",
        "slug": "coffee-maker",
        "description": "Fresh coffee at home",
        "status": "MODERATED",
        "category_id": category_id,
        "images": [{"id": "img-1", "url": "https://example.test/image.jpg", "ordering": 0}],
        "skus": [{"id": SKU_ID, "name": "Black", "price": 12000, "active_quantity": 3, "cost_price": 1, "reserved_quantity": 2}],
    }


def test_catalog_returns_filtered_sorted_products(client, monkeypatch):
    captured = {}

    def fake_get_products(**kwargs):
        captured.update(kwargs)
        return {"items": [public_product()], "total_count": 1, "limit": 20, "offset": 0}

    monkeypatch.setattr(b2b_client, "get_products", fake_get_products)
    response = client.get(f"/api/v1/catalog/products?filter[category_id]={CATEGORY_ID}&sort=new")
    assert response.status_code == 200
    assert captured["category"] == CATEGORY_ID
    assert response.json()["items"][0] == {
        "id": PRODUCT_ID, "name": "Coffee maker", "slug": "coffee-maker", "min_price": 12000,
        "old_price": None, "has_stock": True, "rating": None, "reviews_count": 0,
        "images": [{"id": "img-1", "url": "https://example.test/image.jpg", "alt": None, "ordering": 0, "is_main": True}],
    }


def test_invalid_sort_and_short_q_return_contract_error(client):
    for query in ("?sort=rating", "?q=ab"):
        response = client.get(f"/api/v1/catalog/products{query}")
        assert response.status_code == 400
        assert set(response.json()) == {"code", "message"}


def test_product_card_excludes_seller_only_sku_fields(client, monkeypatch):
    monkeypatch.setattr(b2b_client, "get_product_by_id", lambda _id: public_product())
    response = client.get(f"/api/v1/catalog/products/{PRODUCT_ID}")
    assert response.status_code == 200
    sku = response.json()["skus"][0]
    assert sku["available_quantity"] == 3
    assert "cost_price" not in sku
    assert "reserved_quantity" not in sku


def test_similar_returns_plain_array_with_contract_cards(client, monkeypatch):
    monkeypatch.setattr(b2b_client, "get_product_by_id", lambda _id: public_product())
    monkeypatch.setattr(b2b_client, "get_products", lambda **_: {"items": [public_product(), public_product("00000000-0000-0000-0000-000000000002")], "total_count": 2})
    response = client.get(f"/api/v1/catalog/products/{PRODUCT_ID}/similar?limit=50")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Coffee maker"


def test_category_tree_is_plain_array_and_orphans_return_422(client, monkeypatch):
    categories = [
        {"id": "root", "name": "Root", "parent_id": None},
        {"id": "child", "name": "Child", "parent_id": "root"},
    ]
    monkeypatch.setattr(b2b_client, "get_categories", lambda: categories)
    tree = client.get("/api/v1/catalog/categories/tree")
    assert tree.status_code == 200
    assert tree.json()[0]["children"][0]["path"] == ["root", "child"]

    monkeypatch.setattr(b2b_client, "get_categories", lambda: [{"id": "orphan", "name": "Orphan", "parent_id": "missing"}])
    invalid = client.get("/api/v1/catalog/categories/tree")
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "INVALID_CATEGORY_TREE"
