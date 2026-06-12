from sqlalchemy.orm import Session
from src.models.order import Order, OrderItem
from src.services.b2b_client import b2b_client
import uuid
import httpx


class OrderService:
    def __init__(self, db: Session):
        self.db = db

    def create_order(self, user_id: str, items: list, idempotency_key: str, delivery_address: str = None) -> dict:
        existing = self.db.query(Order).filter(
            Order.idempotency_key == idempotency_key
        ).first()

        if existing:
            return {"status": "existing", "order": self._format_order(existing)}

        if not items:
            return {"code": "INVALID_REQUEST", "message": "items is empty"}

        sku_ids = [item["sku_id"] for item in items]

        try:
            b2b_data = b2b_client.get_products(limit=100, offset=0, ids=",".join(sku_ids))
            b2b_products = {p["id"]: p for p in b2b_data.get("items", [])}
        except Exception:
            return {"code": "B2B_UNAVAILABLE", "message": "B2B service unavailable"}

        failed_items = []
        sku_prices = {}

        for item in items:
            product = None
            sku_data = None

            for pid, pdata in b2b_products.items():
                for s in pdata.get("skus", []):
                    if s.get("id") == item["sku_id"]:
                        product = pdata
                        sku_data = s
                        break
                if product:
                    break

            if not product or not sku_data:
                failed_items.append({
                    "sku_id": item["sku_id"],
                    "requested": item["quantity"],
                    "available": 0,
                    "reason": "SKU_NOT_FOUND"
                })
                continue

            if product.get("status") != "MODERATED":
                failed_items.append({
                    "sku_id": item["sku_id"],
                    "requested": item["quantity"],
                    "available": 0,
                    "reason": "PRODUCT_BLOCKED"
                })
                continue

            if product.get("deleted"):
                failed_items.append({
                    "sku_id": item["sku_id"],
                    "requested": item["quantity"],
                    "available": 0,
                    "reason": "PRODUCT_DELETED"
                })
                continue

            active_qty = sku_data.get("active_quantity", 0)
            if active_qty < item["quantity"]:
                failed_items.append({
                    "sku_id": item["sku_id"],
                    "requested": item["quantity"],
                    "available": active_qty,
                    "reason": "OUT_OF_STOCK" if active_qty == 0 else "INSUFFICIENT_STOCK"
                })
                continue

            sku_prices[item["sku_id"]] = {
                "product_id": product.get("id"),
                "product_title": product.get("title"),
                "sku_name": sku_data.get("name"),
                "unit_price": sku_data.get("price", 0)
            }

        if failed_items:
            return {
                "code": "RESERVE_FAILED",
                "message": "Не удалось зарезервировать товары",
                "failed_items": failed_items
            }

        reserve_items = [{"sku_id": item["sku_id"], "quantity": item["quantity"]} for item in items]

        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{b2b_client.base_url}/api/v1/inventory/reserve",
                    json={
                        "idempotency_key": idempotency_key,
                        "order_id": str(uuid.uuid4()),
                        "items": reserve_items
                    },
                    headers=b2b_client.headers,
                    timeout=10.0
                )

                if response.status_code == 409:
                    reserve_data = response.json()
                    return {
                        "code": "RESERVE_FAILED",
                        "message": "Не удалось зарезервировать товары",
                        "failed_items": reserve_data.get("failed_items", [])
                    }

                response.raise_for_status()
        except Exception:
            return {"code": "B2B_UNAVAILABLE", "message": "B2B service unavailable"}

        order_id = str(uuid.uuid4())
        total_amount = 0

        order = Order(
            id=order_id,
            user_id=user_id,
            status="PAID",
            idempotency_key=idempotency_key,
            delivery_address=delivery_address
        )
        self.db.add(order)

        order_items = []
        for item in items:
            price_info = sku_prices[item["sku_id"]]
            line_total = price_info["unit_price"] * item["quantity"]
            total_amount += line_total

            order_item = OrderItem(
                id=str(uuid.uuid4()),
                order_id=order_id,
                sku_id=item["sku_id"],
                product_id=price_info["product_id"],
                product_title=price_info["product_title"],
                sku_name=price_info["sku_name"],
                quantity=item["quantity"],
                unit_price=price_info["unit_price"],
                line_total=line_total
            )
            order_items.append(order_item)
            self.db.add(order_item)

        order.total_amount = total_amount
        self.db.commit()

        return {"status": "created", "order": self._format_order(order, order_items)}

    def get_order(self, user_id: str, order_id: str) -> dict | None:
        order = self.db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == user_id
        ).first()

        if not order:
            return None

        items = self.db.query(OrderItem).filter(
            OrderItem.order_id == order_id
        ).all()

        return self._format_order(order, items)

    def get_orders(self, user_id: str, limit: int = 20, offset: int = 0, status: str = None) -> dict:
        query = self.db.query(Order).filter(Order.user_id == user_id)

        if status:
            query = query.filter(Order.status == status)

        total = query.count()
        orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

        items = []
        for order in orders:
            items_count = self.db.query(OrderItem).filter(OrderItem.order_id == order.id).count()
            items.append({
                "id": order.id,
                "status": order.status,
                "total_amount": order.total_amount,
                "items_count": items_count,
                "created_at": str(order.created_at) if order.created_at else None,
                "updated_at": str(order.updated_at) if order.updated_at else None
            })

        return {"items": items, "total_count": total, "limit": limit, "offset": offset}

    def _format_order(self, order: Order, items: list = None) -> dict:
        if items is None:
            items = self.db.query(OrderItem).filter(
                OrderItem.order_id == order.id
            ).all()

        formatted_items = [{
            "id": item.id,
            "sku_id": item.sku_id,
            "product_id": item.product_id,
            "product_title": item.product_title,
            "sku_name": item.sku_name,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "line_total": item.line_total
        } for item in items]

        return {
            "id": order.id,
            "status": order.status,
            "items": formatted_items,
            "total_amount": order.total_amount,
            "delivery_address": order.delivery_address,
            "created_at": str(order.created_at) if order.created_at else None,
            "updated_at": str(order.updated_at) if order.updated_at else None
        }
