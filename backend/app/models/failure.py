from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.domain.enums import FailureRecoveryState
from app.models.common import utc_created_at, uuid_pk


class NodeFailure(Base):
    __tablename__ = "node_failures"

    id: Mapped[str] = uuid_pk()
    ambulance_id: Mapped[str] = mapped_column(ForeignKey("ambulance_nodes.id"), nullable=False, index=True)
    failure_type: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    failed_at: Mapped[datetime] = utc_created_at()
    recovery_state: Mapped[str] = mapped_column(
        String(40),
        default=FailureRecoveryState.DETECTADO.value,
        nullable=False,
    )
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ambulance = relationship("AmbulanceNode", back_populates="failures")
