from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.common import utc_created_at, uuid_pk


class SystemEvent(Base):
    __tablename__ = "system_events"

    id: Mapped[str] = uuid_pk()
    emergency_id: Mapped[str | None] = mapped_column(ForeignKey("emergencies.id"), nullable=True, index=True)
    ambulance_id: Mapped[str | None] = mapped_column(ForeignKey("ambulance_nodes.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = utc_created_at()

    emergency = relationship("Emergency", back_populates="events")
    ambulance = relationship("AmbulanceNode", back_populates="events")
