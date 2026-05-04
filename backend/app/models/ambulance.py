from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.domain.enums import AmbulanceState
from app.models.common import utc_created_at, uuid_pk


class AmbulanceNode(Base):
    __tablename__ = "ambulance_nodes"
    __table_args__ = (UniqueConstraint("code", name="uq_ambulance_nodes_code"),)

    id: Mapped[str] = uuid_pk()
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    state: Mapped[str] = mapped_column(String(40), default=AmbulanceState.DISPONIBLE.value, nullable=False)
    simulated_location: Mapped[str] = mapped_column(String(120), nullable=False)
    operational_load: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reliability: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = utc_created_at()

    assignments = relationship("Assignment", back_populates="ambulance")
    recommendations = relationship("AIRecommendation", back_populates="recommended_ambulance")
    events = relationship("SystemEvent", back_populates="ambulance")
    failures = relationship("NodeFailure", back_populates="ambulance")
