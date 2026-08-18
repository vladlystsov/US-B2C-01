from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.schemas.catalog import FacetsResponse, ProductShortListResponse
from src.services.catalog_service import VALID_SORT_VALUES, catalog_service

router = APIRouter(prefix="/api/v1/catalog", tags=["Catalog"])


@router.get("/products", response_model=ProductShortListResponse)
def get_products(
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
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(exc)})
    except Exception:
        raise HTTPException(status_code=502, detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"})


@router.get("/facets", response_model=FacetsResponse, include_in_schema=False)
def get_facets(category_id: Optional[str] = None):
    try:
        return catalog_service.get_facets(category_id=category_id)
    except Exception:
        raise HTTPException(status_code=502, detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"})
