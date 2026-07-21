from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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


class ItemUpdateRequest(BaseModel):
    """design.md 6.6節: 全フィールド任意、指定されたものだけ更新する(exclude_unsetで判定)。

    color_secondary以外は付録どおり非nullable(design.md 6.6節の型は`string`)であり、
    明示的に`null`を送ると422になる。デフォルトのNoneは「未指定」を表す内部値であり、
    exclude_unset=Trueで拾われるフィールドにのみ現れるため実際にDBへ書き込まれることはない。
    """

    category: Literal["outer", "tops", "bottoms", "dress", "shoes", "bag", "hat", "watch", "glasses"] = None  # type: ignore[assignment]
    color_primary: str = Field(default=None, min_length=1, max_length=30)  # type: ignore[assignment]
    color_secondary: str | None = Field(default=None, min_length=1, max_length=30)
    pattern: Literal["無地", "ストライプ", "ボーダー", "チェック", "ドット", "花柄", "ロゴ", "プリント", "カモフラ", "その他"] = None  # type: ignore[assignment]
    material: Literal[
        "コットン", "デニム", "ニット", "レザー", "ナイロン", "フリース", "ウール", "スウェット", "ファー", "ボア", "金属", "樹脂", "その他"
    ] = None  # type: ignore[assignment]
    silhouette: str = Field(default=None, min_length=1, max_length=50)  # type: ignore[assignment]
