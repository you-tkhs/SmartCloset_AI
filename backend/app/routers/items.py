"""design.md 6.3節・6.4節・6.5節・8.6節(b): GET /api/items/{item_id}/status, GET /api/items。lazy stale検出を行う。"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.clothing_item import ClothingItem
from app.schemas.item import ItemListResponse, ItemResponse, ItemStatusResponse
from app.services.pipeline_service import recover_item_if_stale
from app.services.storage_service import to_public_url

router = APIRouter()


def _error(status_code: int, error_code: str, detail: str, retryable: bool) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"detail": detail, "error_code": error_code, "retryable": retryable},
    )


def _to_item_response(item: ClothingItem) -> ItemResponse:
    return ItemResponse(
        id=item.id,
        status=item.status,
        failure_reason=item.failure_reason,
        category=item.category,
        color_primary=item.color_primary,
        color_secondary=item.color_secondary,
        pattern=item.pattern,
        material=item.material,
        silhouette=item.silhouette,
        yolo_pred_class=item.yolo_pred_class,
        yolo_confidence=item.yolo_confidence,
        num_instances=item.num_instances,
        is_user_corrected=item.is_user_corrected,
        original_image_url=to_public_url(item.original_image_path) if item.original_image_path else None,
        transparent_image_url=to_public_url(item.transparent_image_path) if item.transparent_image_path else None,
        original_filename=item.original_filename,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/api/items/{item_id}/status", response_model=ItemStatusResponse)
def get_item_status(item_id: str, db: Session = Depends(get_db)):
    item = db.get(ClothingItem, item_id)
    if item is None:
        raise _error(404, "item_not_found", "指定されたアイテムが見つかりません。", False)

    recover_item_if_stale(db, item)

    return ItemStatusResponse(item_id=item.id, status=item.status, failure_reason=item.failure_reason)


@router.get("/api/items", response_model=ItemListResponse)
def list_items(
    category: str | None = Query(None),
    color: str | None = Query(None),
    pattern: str | None = Query(None),
    material: str | None = Query(None),
    status: str | None = Query(None),
    sort: Literal["created_at_desc", "created_at_asc"] = Query("created_at_desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(ClothingItem).filter(ClothingItem.user_id == 1)

    if category is not None:
        query = query.filter(ClothingItem.category == category)
    if color is not None:
        color_like = f"%{color}%"
        query = query.filter(
            (ClothingItem.color_primary.like(color_like)) | (ClothingItem.color_secondary.like(color_like))
        )
    if pattern is not None:
        query = query.filter(ClothingItem.pattern == pattern)
    if material is not None:
        query = query.filter(ClothingItem.material == material)
    if status is not None:
        query = query.filter(ClothingItem.status == status)

    total = query.count()

    order_column = ClothingItem.created_at.asc() if sort == "created_at_asc" else ClothingItem.created_at.desc()
    items = query.order_by(order_column).offset((page - 1) * page_size).limit(page_size).all()

    return ItemListResponse(
        items=[_to_item_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
