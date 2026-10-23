
from sqlalchemy import String, DECIMAL
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.database import Base


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    latitude: Mapped[float] = mapped_column(
        DECIMAL(10, 7),
        nullable=False,
    )
    longitude: Mapped[float] = mapped_column(
        DECIMAL(10, 7),
        nullable=False,
    )
    location_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    assessments = relationship(
        "Assessment",
        back_populates="location",
        cascade="all, delete-orphan",
    )
    infrastructure_observations = relationship(
        "InfrastructureObservation",
        back_populates="location",
        cascade="all, delete-orphan",
    )
    interventions = relationship(
        "Intervention",
        back_populates="location",
        cascade="all, delete-orphan",
    )
