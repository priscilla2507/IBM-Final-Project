
from sqlalchemy.orm import Session

from app.models.optimization_run import OptimizationRun
from app.models.optimization_recommendation import OptimizationRecommendation
from app.services.optimizer_service import optimize_interventions
from app.services.gemini_service import analyze_location_interventions
from app.services.weather_service import find_location, get_weather
from app.services.worldpop_service import get_population_near_landmark


def build_intervention_candidates(
    location_name: str,
    temperature: float,
    humidity: float,
    apparent_temperature: float,
) -> tuple[list[dict], int, str]:
    """
    Build prototype intervention candidates using current weather.

    Costs and benefit scores are illustrative planning assumptions,
    not verified local quotations or measured health outcomes.
    """

    heat_score = max(
        0,
        min(
            100,
            round(
                max(0, apparent_temperature - 25) * 4
                + humidity * 0.2
            ),
        ),
    )

    if heat_score >= 70:
        risk_level = "High"
    elif heat_score >= 40:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    # Illustrative planning costs, not verified local prices.
    intervention_catalog = [
        {
            "name": "Public Drinking Water Station",
            "cost": 15000,
            "base_benefit": 25,
            "description": "Provide accessible drinking water for heat relief.",
        },
        {
            "name": "Plant Shade Trees",
            "cost": 20000,
            "base_benefit": 35,
            "description": "Increase shade along exposed public areas.",
        },
        {
            "name": "Cool Roof Coating",
            "cost": 25000,
            "base_benefit": 30,
            "description": "Reduce heat absorption on suitable roofs.",
        },
        {
            "name": "Install Shade Structures",
            "cost": 30000,
            "base_benefit": 40,
            "description": "Create shaded spaces in exposed public areas.",
        },
        {
            "name": "Cooling Shelter",
            "cost": 50000,
            "base_benefit": 60,
            "description": "Provide a designated cooling and rest space.",
        },
    ]

    risk_bonus = round(heat_score * 0.15)
    candidates = []

    for candidate_id, item in enumerate(intervention_catalog, start=1):
        benefit = min(100, item["base_benefit"] + risk_bonus)

        candidates.append(
            {
                "id": candidate_id,
                "intervention_id": None,
                "location_name": location_name,
                "intervention_type": item["name"],
                "estimated_cost": item["cost"],
                "benefit_score": benefit,
                "is_feasible": True,
                "depends_on_intervention_id": None,
                "incompatibility_group": None,
                "is_illustrative": True,
                "explanation": (
                    f"{item['description']} "
                    f"Weather-based risk: {risk_level} "
                    f"(score {heat_score}/100). "
                    "Planning cost and benefit are illustrative. "
                    "Site suitability has not yet been verified."
                ),
            }
        )

    return candidates, heat_score, risk_level


def run_and_save_optimization(
    db: Session,
    budget: int,
    location_name: str,
) -> dict:
    if budget <= 0:
        raise ValueError("Budget must be greater than zero.")

    if not location_name or len(location_name.strip()) < 2:
        raise ValueError("Please provide a valid location name.")

    # 1. Resolve the location.
    geo = find_location(location_name.strip())

    latitude = geo["latitude"]
    longitude = geo["longitude"]

    
    # 1. Resolve the location.
    geo = find_location(location_name.strip())

    latitude = geo["latitude"]
    longitude = geo["longitude"]

    # Initialize the name before appending state or country.
    resolved_name = geo["name"]

    if geo.get("admin1"):
        resolved_name += f", {geo['admin1']}"

    if geo.get("country"):
        resolved_name += f", {geo['country']}"

    # Retrieve WorldPop data without interrupting optimization
    # if the external service is temporarily unavailable.
    population_data = None

    try:
        population_data = get_population_near_landmark(
            latitude=latitude,
            longitude=longitude,
        )
        print("WorldPop response:", population_data)

    except Exception as exc:
        print(f"WorldPop unavailable. Reason: {exc}")

    # Retrieve population data without breaking optimization if unavailable.
    population_data = None

    try:
        population_data = get_population_near_landmark(
            latitude=latitude,
            longitude=longitude,
        )
        print("WorldPop response:", population_data)

    except Exception as exc:
        print(f"WorldPop unavailable. Reason: {exc}")

    if geo.get("admin1"):
        resolved_name += f", {geo['admin1']}"

    if geo.get("country"):
        resolved_name += f", {geo['country']}"

    # 2. Fetch current weather.
    weather_data = get_weather(latitude, longitude)
    current = weather_data.get("current", {})

    temperature = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    apparent_temperature = current.get("apparent_temperature")

    if temperature is None or humidity is None:
        raise RuntimeError(
            "Weather data is missing temperature or humidity."
        )

    if apparent_temperature is None:
        apparent_temperature = temperature

    temperature = float(temperature)
    humidity = float(humidity)
    apparent_temperature = float(apparent_temperature)

    # 3. Build weather-based intervention candidates.
    candidates, heat_score, risk_level = build_intervention_candidates(
        resolved_name,
        temperature,
        humidity,
        apparent_temperature,
    )

    # 4. Try Gemini analysis. If it fails, retain the weather-based scores.
    gemini_used = False
    gemini_summary = (
        "Gemini analysis is unavailable. Recommendations use "
        "weather-derived planning scores and the intervention catalog."
    )

    try:
        gemini_analysis = analyze_location_interventions(
            resolved_name,
            {
                "current": current,
                "heat_score": heat_score,
                "risk_level": risk_level,
            },
            candidates,
        )

        gemini_recommendations = {
            item["intervention_type"]: item
            for item in gemini_analysis.get("recommendations", [])
        }

        # Apply Gemini results only if all candidates have matching results.
        expected_names = {
            candidate["intervention_type"] for candidate in candidates
        }

        if set(gemini_recommendations.keys()) != expected_names:
            raise ValueError(
                "Gemini recommendations do not match the intervention catalog."
            )

        for candidate in candidates:
            ai_result = gemini_recommendations[
                candidate["intervention_type"]
            ]

            candidate["benefit_score"] = ai_result["benefit_score"]
            candidate["explanation"] = (
                f"{candidate['explanation']} "
                f"Gemini analysis: {ai_result['explanation']}"
            )

        gemini_summary = gemini_analysis.get(
            "location_summary",
            "Gemini analyzed the location and weather conditions.",
        )
        gemini_used = True

    except Exception as exc:
        # Includes quota errors, API failures, and invalid Gemini responses.
        # Keep the original weather-based candidate scores and explanations.
        print(
            "Gemini unavailable. Continuing with weather-based "
            f"recommendations. Reason: {exc}"
        )

    # 5. Run OR-Tools regardless of whether Gemini succeeded.
    result = optimize_interventions(candidates, budget)

    try:
        # 6. Save the optimization run.
        run = OptimizationRun(
            budget=budget,
            total_cost=result["total_cost"],
            total_benefit_score=result["total_benefit_score"],
            recommendations_json={
                "location_name": resolved_name,
                "weather": {
                    "temperature": temperature,
                    "humidity": humidity,
                    "apparent_temperature": apparent_temperature,
                    "weather_time": current.get("time"),
                },
                "heat_score": heat_score,
                "risk_level": risk_level,
                "gemini_used": gemini_used,
                "gemini_location_summary": gemini_summary,
                "recommendations": result["recommendations"],
                "costs_are_illustrative": True,
            },
        )

        db.add(run)
        db.flush()

        # 7. Save recommendations without fake intervention IDs.
        for recommendation in result["recommendations"]:
            db.add(
                OptimizationRecommendation(
                    optimization_run_id=run.id,
                    intervention_id=None,
                    location_name=resolved_name,
                    intervention_type=recommendation["intervention_type"],
                    estimated_cost=recommendation["estimated_cost"],
                    benefit_score=recommendation["benefit_score"],
                    explanation=recommendation["explanation"],
                )
            )

        db.commit()
        db.refresh(run)

        # 8. Return the response.
        return {
            "optimization_run_id": run.id,
            "budget": budget,
            "location_name": resolved_name,
            "weather": {
                "temperature": temperature,
                "humidity": humidity,
                "apparent_temperature": apparent_temperature,
                "time": current.get("time"),
            },
            "heat_score": heat_score,
            "risk_level": risk_level,
            "gemini_used": gemini_used,
            "gemini_location_summary": gemini_summary,
            "total_cost": result["total_cost"],
            "total_benefit_score": result["total_benefit_score"],
            "remaining_budget": budget - result["total_cost"],
            "recommendations": result["recommendations"],
            "costs_are_illustrative": True,

            # WorldPop population data
            "estimated_resident_population": (
                population_data["estimated_resident_population"]
                if population_data else None
            ),
            "population_data_year": (
                population_data["data_year"]
                if population_data else None
            ),
            "population_source": (
                population_data["source"]
                if population_data else None
            ),
            "population_area_km2": (
                population_data["area_km2"]
                if population_data else None
            ),
        }

    except Exception:
        db.rollback()
        raise
