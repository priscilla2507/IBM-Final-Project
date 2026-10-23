
from pydantic import BaseModel, Field


class OptimizationRequest(BaseModel):
    budget: int = Field(
        gt=0,
        description="Maximum available budget in Indian Rupees (INR)",
        examples=[50000],
    )

    location_name: str = Field(
        min_length=2,
        max_length=150,
        description="Name of the target city or location",
        examples=["Hyderabad, Telangana"],
    )


class RecommendationResponse(BaseModel):
    intervention_id: int | None = None
    location_name: str
    intervention_type: str
    estimated_cost: int
    benefit_score: int
    explanation: str



class OptimizationResponse(BaseModel):
    optimization_run_id: int
    budget: int
    total_cost: int
    total_benefit_score: int
    remaining_budget: int
    recommendations: list[RecommendationResponse]

    # WorldPop population estimate
    estimated_resident_population: int | None = None
    population_data_year: int | None = None
    population_source: str | None = None
    population_area_km2: float | None = None
