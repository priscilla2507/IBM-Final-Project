
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    optimization_run_id: Mapped[int] = mapped_column(
        ForeignKey("optimization_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intervention_id: Mapped[int | None] = mapped_column(
        ForeignKey("interventions.id", ondelete="SET NULL"),
        nullable=True,
    )

    location_name: Mapped[str] = mapped_column(String(150), nullable=False)
    intervention_type: Mapped[str] = mapped_column(String(120), nullable=False)
    estimated_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    benefit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    optimization_run = relationship(
        "OptimizationRun", back_populates="recommendations"
    )
    intervention = relationship("Intervention")
