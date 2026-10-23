
from datetime import datetime

from sqlalchemy import (
    DateTime, DECIMAL, ForeignKey, Integer, String,
    CheckConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Assessment(Base):
    __tablename__ = "assessments"

    __table_args__ = (
        CheckConstraint("temperature BETWEEN -50 AND 70"),
        CheckConstraint("humidity BETWEEN 0 AND 100"),
        CheckConstraint("risk_score BETWEEN 0 AND 100"),
        Index("ix_assessments_location_assessed", "location_id", "assessed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    temperature: Mapped[float] = mapped_column(DECIMAL(5, 2), nullable=False)
    humidity: Mapped[float] = mapped_column(DECIMAL(5, 2), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(30), nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    location = relationship("Location", back_populates="assessments")
