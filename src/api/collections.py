from fastapi import APIRouter, Depends, HTTPException, Query
from src.schemas.collection import CollectionsListResponse, CollectionProductsResponse
from src.services.collection_service import CollectionService
from src.database import get_db
from sqlalchemy.orm import Session


router = APIRouter(tags=["Collections"])


@router.get("/api/v1/main/collections", response_model=CollectionsListResponse)
def get_collections(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0)
):
    service = CollectionService(db)
    return service.get_collections(limit=limit, offset=offset)


@router.get("/api/v1/collections/{collection_id}/products", response_model=CollectionProductsResponse)
def get_collection_products(
    collection_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    service = CollectionService(db)
    result = service.get_collection_products(collection_id, limit=limit, offset=offset)

    if result is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Collection not found"})

    return result
