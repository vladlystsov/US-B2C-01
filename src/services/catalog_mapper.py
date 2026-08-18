from __future__ import annotations

from typing import Any


def image_ref(image: Any, ordering: int = 0) -> dict | None:
    """Normalise a B2B image to the B2C ImageRef shape."""
    if not image:
        return None
    if isinstance(image, str):
        return {"id": f"legacy-image-{ordering}", "url": image, "ordering": ordering}
    if not isinstance(image, dict):
        return None

    url = image.get("url") or image.get("image")
    if not url:
        return None
    return {
        "id": str(image.get("id") or f"legacy-image-{ordering}"),
        "url": url,
        "alt": image.get("alt"),
        "ordering": image.get("ordering", ordering),
        "is_main": image.get("is_main", ordering == 0),
    }


def image_refs(images: list | None) -> list[dict]:
    return [ref for index, image in enumerate(images or []) if (ref := image_ref(image, index))]


def product_images(product: dict) -> list[dict]:
    images = image_refs(product.get("images"))
    if images:
        return images
    for sku in product.get("skus", []) or []:
        images = image_refs(sku.get("images") or [sku.get("image")])
        if images:
            return images
    if product.get("cover_image"):
        return image_refs([product["cover_image"]])
    return []


def active_skus(product: dict) -> list[dict]:
    return [sku for sku in product.get("skus", []) or [] if sku.get("active_quantity", 0) > 0]


def catalog_card(product: dict) -> dict:
    """Map a B2B public product to B2C CatalogProductCard without seller-only fields."""
    available_skus = active_skus(product)
    listed_price = product.get("min_price")
    min_price = listed_price if listed_price is not None else min(
        (sku.get("price", 0) for sku in available_skus), default=0
    )
    return {
        "id": product.get("id"),
        "name": product.get("name") or product.get("title"),
        "slug": product.get("slug"),
        "min_price": min_price,
        "old_price": product.get("old_price"),
        "has_stock": bool(available_skus) if product.get("skus") is not None else True,
        "rating": product.get("rating"),
        "reviews_count": product.get("reviews_count", 0),
        "images": product_images(product),
    }


def catalog_detail(product: dict) -> dict:
    card = catalog_card(product)
    skus = []
    for sku in product.get("skus", []) or []:
        images = image_refs(sku.get("images") or [sku.get("image")])
        skus.append(
            {
                "id": sku.get("id"),
                "name": sku.get("name"),
                "sku_code": sku.get("sku_code") or sku.get("article"),
                "price": sku.get("price", 0),
                "old_price": sku.get("old_price"),
                "available_quantity": sku.get("active_quantity", 0),
                "attributes": sku.get("attributes") or sku.get("characteristics", {}),
                "images": images,
            }
        )

    card.update(
        {
            "description": product.get("description", ""),
            "attributes": product.get("attributes") or product.get("characteristics", {}),
            "skus": skus,
        }
    )
    return card


def cart_product_data(product: dict, sku_id: str) -> dict | None:
    for sku in product.get("skus", []) or []:
        if sku.get("id") == sku_id:
            images = image_refs(sku.get("images") or [sku.get("image")]) or product_images(product)
            return {
                "sku_id": sku_id,
                "product_id": product.get("id"),
                "name": " — ".join(filter(None, [product.get("title") or product.get("name"), sku.get("name")])),
                "sku_code": sku.get("sku_code") or sku.get("article"),
                "unit_price": sku.get("price", product.get("min_price", 0)),
                "available_quantity": sku.get("active_quantity", 0),
                "image": images[0] if images else None,
            }
    return None
