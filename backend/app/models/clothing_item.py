from datetime import datetime, timezone

from sqlalchemy import REAL, Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ClothingItem(Base):
    __tablename__ = "clothing_items"
    __table_args__ = (
        Index("ix_clothing_items_user_category", "user_id", "category"),
        Index("ix_clothing_items_user_status", "user_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="processing")
    failure_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    color_primary: Mapped[str | None] = mapped_column(String(30), nullable=True)
    color_secondary: Mapped[str | None] = mapped_column(String(30), nullable=True)
    pattern: Mapped[str | None] = mapped_column(String(20), nullable=True)
    material: Mapped[str | None] = mapped_column(String(20), nullable=True)
    silhouette: Mapped[str | None] = mapped_column(String(50), nullable=True)
    yolo_pred_class: Mapped[str | None] = mapped_column(String(20), nullable=True)
    yolo_confidence: Mapped[float | None] = mapped_column(REAL, nullable=True)
    num_instances: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_user_corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idempotency_key: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    upload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    original_image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    transparent_image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    mask_image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    annotated_image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
