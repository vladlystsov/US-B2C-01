from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from src.schemas.catalog import FacetsResponse, ProductShortListResponse
from src.services.catalog_service import catalog_service

router = APIRouter(prefix="/api/v1/catalog", tags=["Catalog"])


def _attribute_filters(request: Request) -> dict[str, str | list[str]]:
    """Translate B2C `filter[attributes][key]` into B2B `filters[key]`.

    B2C nests dynamic attributes inside CatalogFilter, while B2B exposes its
    characteristic filters as a standalone deepObject. Existing flat filter
    spellings remain accepted for backwards compatibility.
    """
    reserved = {"category_id", "price_min", "price_max", "seller_id"}
    attributes: dict[str, str | list[str]] = {}
    for key, value in request.query_params.multi_items():
        attribute = None
        for prefix in ("filter[attributes][", "filters["):
            if key.startswith(prefix) and key.endswith("]"):
                attribute = key[len(prefix):-1]
                break
        if attribute is None and key.startswith("filter[") and key.endswith("]"):
            candidate = key[len("filter["):-1]
            if candidate not in reserved and "][" not in candidate:
                attribute = candidate
        if attribute and attribute not in reserved:
            current = attributes.get(attribute)
            if current is None:
                attributes[attribute] = value
            elif isinstance(current, list):
                current.append(value)
            else:
                attributes[attribute] = [current, value]
    return attributes


@router.get("/products", response_model=ProductShortListResponse)
def get_products(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None, max_length=200),
    sort: Optional[str] = None,
    category_id: Optional[str] = Query(None, alias="filter[category_id]"),
    price_min: Optional[int] = Query(None, ge=0, alias="filter[price_min]"),
    price_max: Optional[int] = Query(None, ge=0, alias="filter[price_max]"),
    seller_id: Optional[str] = Query(None, alias="filter[seller_id]"),
):
    try:
        return catalog_service.get_products(
            limit=limit,
            offset=offset,
            category_id=category_id,
            q=q,
            sort=sort,
            price_min=price_min,
            price_max=price_max,
            seller_id=seller_id,
            attributes=_attribute_filters(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(exc)})
    except Exception:
        raise HTTPException(status_code=502, detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"})


@router.get("/facets", response_model=FacetsResponse, include_in_schema=False)
def get_facets(request: Request, category_id: Optional[str] = None):
    try:
        return catalog_service.get_facets(category_id=category_id, attributes=_attribute_filters(request))
    except Exception:
        raise HTTPException(status_code=502, detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"})
