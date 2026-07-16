"""design.md 6.3節・8.6節(b): GET /api/items/{item_id}/status。lazy stale検出を行う。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.clothing_item import ClothingItem
from app.schemas.item import ItemStatusResponse
from app.services.pipeline_service import recover_item_if_stale

router = APIRouter()


def _error(status_code: int, error_code: str, detail: str, retryable: bool) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"detail": detail, "error_code": error_code, "retryable": retryable},
    )


@router.get("/api/items/{item_id}/status", response_model=ItemStatusResponse)
def get_item_status(item_id: str, db: Session = Depends(get_db)):
    item = db.get(ClothingItem, item_id)
    if item is None:
        raise _error(404, "item_not_found", "指定されたアイテムが見つかりません。", False)

    recover_item_if_stale(db, item)

    return ItemStatusResponse(item_id=item.id, status=item.status, failure_reason=item.failure_reason)
