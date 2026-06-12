from src.services.b2b_client import b2b_client


class ProductCardService:
    def get_product_card(self, product_id: str) -> dict:
        b2b_data = b2b_client.get_product_by_id(product_id)

        if not b2b_data:
            return None

        if b2b_data.get("status") not in ["MODERATED"]:
            return None
        if b2b_data.get("deleted"):
            return None

        skus = []
        prices = []
        has_stock = False

        for sku in b2b_data.get("skus", []):
            available = sku.get("active_quantity", 0)
            if available > 0:
                has_stock = True
                prices.append(sku.get("price", 0))

            skus.append({
                "id": sku.get("id"),
                "name": sku.get("name"),
                "price": sku.get("price", 0),
                "discount": sku.get("discount", 0),
                "image": sku.get("image"),
                "available_quantity": available,
                "characteristics": sku.get("characteristics", [])
            })

        min_price = min(prices) if prices else 0

        return {
            "id": b2b_data.get("id"),
            "name": b2b_data.get("title"),
            "description": b2b_data.get("description"),
            "slug": b2b_data.get("slug"),
            "images": b2b_data.get("images", []),
            "characteristics": b2b_data.get("characteristics", []),
            "skus": skus,
            "min_price": min_price,
            "has_stock": has_stock
        }


product_card_service = ProductCardService()
