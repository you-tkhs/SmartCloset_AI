from datetime import datetime

from pydantic import BaseModel


class UploadAcceptedResponse(BaseModel):
    item_id: str
    status: str
    failure_reason: str | None = None


class ItemStatusResponse(BaseModel):
    item_id: str
    status: str
    failure_reason: str | None = None


class ItemResponse(BaseModel):
    """design.md 6.5節: 内部ファイルパスは含まずURLのみを返す。"""

    id: str
    status: str
    failure_reason: str | None = None
    category: str | None = None
    color_primary: str | None = None
    color_secondary: str | None = None
    pattern: str | None = None
    material: str | None = None
    silhouette: str | None = None
    yolo_pred_class: str | None = None
    yolo_confidence: float | None = None
    num_instances: int | None = None
    is_user_corrected: bool
    original_image_url: str | None = None
    transparent_image_url: str | None = None
    original_filename: str | None = None
    created_at: datetime
    updated_at: datetime


class ItemListResponse(BaseModel):
    items: list[ItemResponse]
    total: int
    page: int
    page_size: int
