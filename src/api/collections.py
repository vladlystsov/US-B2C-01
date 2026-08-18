from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas.collection import CollectionMetadata, CollectionProductsResponse
from src.services.collection_service import CollectionService

router = APIRouter(tags=["Collections"])


@router.get("/api/v1/catalog/collections", response_model=list[CollectionMetadata])
def get_collections(db: Session = Depends(get_db)):
    return CollectionService(db).get_collections()


@router.get("/api/v1/collections/{collection_id}/products", response_model=CollectionProductsResponse, include_in_schema=False)
def get_collection_products(collection_id: str, db: Session = Depends(get_db)):
    result = CollectionService(db).get_collection_products(collection_id)
    if result is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Collection not found"})
    return result
