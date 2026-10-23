
from ortools.sat.python import cp_model


def optimize_interventions(interventions: list[dict], budget: int) -> dict:
    """
    Select interventions that maximize total benefit within the budget.

    Each intervention dictionary should contain:
    id, location_name, intervention_type, estimated_cost,
    benefit_score, is_feasible, depends_on_intervention_id,
    incompatibility_group, and is_illustrative.
    """
    if budget <= 0:
        raise ValueError("Budget must be greater than zero.")

    candidates = [
        item for item in interventions
        if item["is_feasible"]
        and item["estimated_cost"] > 0
        and item["benefit_score"] >= 0
    ]

    if not candidates:
        return {
            "total_cost": 0,
            "total_benefit_score": 0,
            "recommendations": [],
        }

    model = cp_model.CpModel()
    selected = {
        item["id"]: model.new_bool_var(f"intervention_{item['id']}")
        for item in candidates
    }

    model.add(
        sum(
            item["estimated_cost"] * selected[item["id"]]
            for item in candidates
        ) <= budget
    )

    by_id = {item["id"]: item for item in candidates}

    # A dependent intervention requires its prerequisite.
    for item in candidates:
            dependency_id = item.get("depends_on_intervention_id")

            if dependency_id is not None:
                if dependency_id not in selected:
                    model.add(selected[item["id"]] == 0)
                else:
                    model.add(
                        selected[item["id"]] <= selected[dependency_id]
                    )


    # At most one intervention from each incompatibility group.
    groups = {}
    for item in candidates:
        group = item.get("incompatibility_group")
        if group:
            groups.setdefault(group, []).append(selected[item["id"]])

    for group_variables in groups.values():
        model.add(sum(group_variables) <= 1)

    model.maximize(
        sum(
            item["benefit_score"] * selected[item["id"]]
            for item in candidates
        )
    )

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 42

    status = solver.solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("The optimizer could not find a feasible solution.")

    recommendations = []
    total_cost = 0
    total_benefit = 0

    for item in candidates:
        if solver.value(selected[item["id"]]):
            cost = item["estimated_cost"]
            benefit = item["benefit_score"]

            recommendations.append({
                "intervention_id": item.get("intervention_id"),
                "location_name": item["location_name"],
                "intervention_type": item["intervention_type"],
                "estimated_cost": cost,
                "benefit_score": benefit,
               "explanation": (
                item.get("explanation", "Selected by the budget optimizer.")
                + " Cost and benefit are illustrative estimates."
                if item.get("is_illustrative", True)
                else item.get("explanation", "Selected by the budget optimizer.")
                    + " Cost and benefit are based on supplied data."
                ),
            })

            total_cost += cost
            total_benefit += benefit

    recommendations.sort(key=lambda item: item["intervention_type"])

    return {
        "total_cost": total_cost,
        "total_benefit_score": total_benefit,
        "recommendations": recommendations,
    }
