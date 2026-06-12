from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from src.schemas.catalog import ProductShortListResponse, FacetsResponse
from src.services.catalog_service import catalog_service, VALID_SORT_VALUES

router = APIRouter(prefix="/api/v1", tags=["Catalog"])


@router.get("/products", response_model=ProductShortListResponse)
def get_products(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
):
    try:
        result = catalog_service.get_products(
            limit=limit,
            offset=offset,
            category_id=category_id,
            search=search,
            sort=sort
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_REQUEST", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"}
        )


@router.get("/catalog/facets", response_model=FacetsResponse)
def get_facets(
    category_id: Optional[str] = None,
):
    try:
        result = catalog_service.get_facets(category_id=category_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"}
        )
