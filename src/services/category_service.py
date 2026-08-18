from __future__ import annotations

import httpx

from src.services.b2b_client import b2b_client


class OrphanCategoryError(ValueError):
    pass


class CategoryService:
    def _categories(self) -> list[dict]:
        return b2b_client.get_categories()

    @staticmethod
    def _normalise(categories: list[dict]) -> tuple[list[dict], dict[str, dict]]:
        by_id = {str(category["id"]): {**category, "id": str(category["id"])} for category in categories}
        for category in by_id.values():
            parent_id = category.get("parent_id")
            if parent_id is not None and str(parent_id) not in by_id:
                raise OrphanCategoryError(f"Category {category['id']} refers to missing parent {parent_id}")

        def category_ref(category: dict) -> dict:
            chain: list[dict] = []
            current = category
            seen: set[str] = set()
            while current:
                current_id = current["id"]
                if current_id in seen:
                    raise OrphanCategoryError(f"Category hierarchy contains a cycle at {current_id}")
                seen.add(current_id)
                chain.append(current)
                parent_id = current.get("parent_id")
                current = by_id.get(str(parent_id)) if parent_id is not None else None
            chain.reverse()
            return {
                "id": category["id"],
                "name": category.get("name", ""),
                "parent_id": str(category["parent_id"]) if category.get("parent_id") is not None else None,
                "level": len(chain) - 1,
                "path": [node["id"] for node in chain],
            }

        refs = [category_ref(category) for category in by_id.values()]
        return refs, by_id

    def get_categories(self) -> list[dict]:
        refs, _ = self._normalise(self._categories())
        return sorted(refs, key=lambda item: (item["level"], item["name"].lower()))

    def get_category_tree(self) -> list[dict]:
        refs = self.get_categories()
        nodes = {item["id"]: {**item, "children": []} for item in refs}
        roots = []
        for node in nodes.values():
            if node["parent_id"] is None:
                roots.append(node)
            else:
                nodes[node["parent_id"]]["children"].append(node)
        for node in nodes.values():
            node["children"].sort(key=lambda item: item["name"].lower())
        return sorted(roots, key=lambda item: item["name"].lower())

    def get_breadcrumbs(self, category_id: str | None = None, product_id: str | None = None) -> list[dict] | dict | None:
        if bool(category_id) == bool(product_id):
            return {"error": "ambiguous_param" if category_id else "missing_param"}
        if product_id:
            try:
                product = b2b_client.get_product_by_id(product_id)
            except httpx.HTTPStatusError:
                return None
            category_id = product.get("category_id") or product.get("category", {}).get("id")
            if not category_id:
                return None

        for category in self.get_categories():
            if category["id"] == str(category_id):
                refs = {item["id"]: item for item in self.get_categories()}
                return [refs[item_id] for item_id in category["path"]]
        return None


category_service = CategoryService()
