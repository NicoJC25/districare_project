import uuid

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column


def uuid_pk() -> Mapped[str]:
    return mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


def utc_created_at() -> Mapped[object]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
