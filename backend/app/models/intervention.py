
from sqlalchemy import (
    Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Intervention(Base):
    __tablename__ = "interventions"

    __table_args__ = (
        CheckConstraint("estimated_cost > 0"),
        CheckConstraint("benefit_score BETWEEN 0 AND 100"),
        Index("ix_interventions_location_feasible", "location_id", "is_feasible"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    intervention_type: Mapped[str] = mapped_column(String(120), nullable=False)
    estimated_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    benefit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    is_feasible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    feasibility_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    depends_on_intervention_id: Mapped[int | None] = mapped_column(
        ForeignKey("interventions.id", ondelete="SET NULL"), nullable=True
    )
    incompatibility_group: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    is_illustrative: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    location = relationship("Location", back_populates="interventions")
    depends_on = relationship(
        "Intervention",
        remote_side="Intervention.id",
        foreign_keys=[depends_on_intervention_id],
    )
