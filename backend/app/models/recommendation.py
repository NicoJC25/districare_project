from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.common import utc_created_at, uuid_pk


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id: Mapped[str] = uuid_pk()
    emergency_id: Mapped[str] = mapped_column(ForeignKey("emergencies.id"), nullable=False, index=True)
    recommended_ambulance_id: Mapped[str | None] = mapped_column(ForeignKey("ambulance_nodes.id"), nullable=True)
    calculated_priority: Mapped[int] = mapped_column(Integer, nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    criteria: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = utc_created_at()

    emergency = relationship("Emergency", back_populates="recommendations")
    recommended_ambulance = relationship("AmbulanceNode", back_populates="recommendations")
