from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.domain.enums import EmergencyState
from app.models.common import utc_created_at, uuid_pk


class Emergency(Base):
    __tablename__ = "emergencies"

    id: Mapped[str] = uuid_pk()
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    simulated_location: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(40), default=EmergencyState.REGISTRADA.value, nullable=False)
    created_at: Mapped[datetime] = utc_created_at()
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assignments = relationship("Assignment", back_populates="emergency")
    recommendations = relationship("AIRecommendation", back_populates="emergency")
    events = relationship("SystemEvent", back_populates="emergency")
