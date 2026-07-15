from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CoordinateLog(Base):
    __tablename__ = "coordinate_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    request_text: Mapped[str] = mapped_column(Text, nullable=False)
    weather_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggestion_text: Mapped[str] = mapped_column(Text, nullable=False)
    styling_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_item_ids: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
