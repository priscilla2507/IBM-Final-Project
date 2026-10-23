
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    __table_args__ = (
        CheckConstraint("budget >= 0"),
        CheckConstraint("total_cost >= 0"),
        CheckConstraint("total_cost <= budget"),
        CheckConstraint("total_benefit_score >= 0"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    budget: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_benefit_score: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    recommendations_json: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    recommendations = relationship(
        "OptimizationRecommendation",
        back_populates="optimization_run",
        cascade="all, delete-orphan",
    )
