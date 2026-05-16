from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, and_
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.domain.enums import AssignmentState
from app.models.common import utc_created_at, uuid_pk


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[str] = uuid_pk()
    emergency_id: Mapped[str] = mapped_column(ForeignKey("emergencies.id"), nullable=False, index=True)
    ambulance_id: Mapped[str] = mapped_column(ForeignKey("ambulance_nodes.id"), nullable=False, index=True)
    recommendation_id: Mapped[str | None] = mapped_column(ForeignKey("ai_recommendations.id"), nullable=True, index=True)
    recommended_ambulance_id: Mapped[str | None] = mapped_column(
        ForeignKey("ambulance_nodes.id"),
        nullable=True,
        index=True,
    )
    state: Mapped[str] = mapped_column(String(40), default=AssignmentState.PENDIENTE.value, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assigned_at: Mapped[datetime] = utc_created_at()
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reassignment_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assignment_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    emergency = relationship("Emergency", back_populates="assignments")
    ambulance = relationship("AmbulanceNode", foreign_keys=[ambulance_id], back_populates="assignments")
    recommended_ambulance = relationship("AmbulanceNode", foreign_keys=[recommended_ambulance_id])
    recommendation = relationship("AIRecommendation", back_populates="assignments")


Index(
    "uq_active_confirmed_assignment_per_emergency",
    Assignment.emergency_id,
    unique=True,
    postgresql_where=and_(
        Assignment.active.is_(True),
        Assignment.state == AssignmentState.CONFIRMADA.value,
    ),
    sqlite_where=and_(
        Assignment.active.is_(True),
        Assignment.state == AssignmentState.CONFIRMADA.value,
    ),
)

Index(
    "uq_active_confirmed_assignment_per_ambulance",
    Assignment.ambulance_id,
    unique=True,
    postgresql_where=and_(
        Assignment.active.is_(True),
        Assignment.state == AssignmentState.CONFIRMADA.value,
    ),
    sqlite_where=and_(
        Assignment.active.is_(True),
        Assignment.state == AssignmentState.CONFIRMADA.value,
    ),
)
