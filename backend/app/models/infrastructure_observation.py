
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InfrastructureObservation(Base):
    __tablename__ = "infrastructure_observations"

    __table_args__ = (
        CheckConstraint("trees_detected >= 0"),
        Index("ix_observations_location_observed", "location_id", "observed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    shade_status: Mapped[str] = mapped_column(String(50), nullable=False)
    trees_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shelter_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    location = relationship(
        "Location", back_populates="infrastructure_observations"
    )
