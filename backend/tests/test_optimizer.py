
from app.services.optimizer_service import optimize_interventions


def make_intervention(
    id,
    cost,
    benefit,
    feasible=True,
    dependency=None,
    group=None,
):
    return {
        "id": id,
        "location_name": "Test Location",
        "intervention_type": f"Intervention {id}",
        "estimated_cost": cost,
        "benefit_score": benefit,
        "is_feasible": feasible,
        "depends_on_intervention_id": dependency,
        "incompatibility_group": group,
        "is_illustrative": True,
    }


def test_selects_best_combination_within_budget():
    interventions = [
        make_intervention(1, 30000, 40),
        make_intervention(2, 20000, 35),
        make_intervention(3, 50000, 60),
    ]

    result = optimize_interventions(interventions, 50000)

    assert result["total_cost"] == 50000
    assert result["total_benefit_score"] == 75
    assert {r["intervention_id"] for r in result["recommendations"]} == {1, 2}


def test_no_intervention_fits_budget():
    interventions = [
        make_intervention(1, 15000, 25),
        make_intervention(2, 30000, 40),
    ]

    result = optimize_interventions(interventions, 10000)

    assert result["total_cost"] == 0
    assert result["total_benefit_score"] == 0
    assert result["recommendations"] == []


def test_infeasible_interventions_are_excluded():
    interventions = [
        make_intervention(1, 10000, 100, feasible=False),
        make_intervention(2, 20000, 30),
    ]

    result = optimize_interventions(interventions, 30000)

    assert {r["intervention_id"] for r in result["recommendations"]} == {2}


def test_dependency_requires_prerequisite():
    interventions = [
        make_intervention(1, 20000, 10),
        make_intervention(2, 10000, 50, dependency=1),
    ]

    result = optimize_interventions(interventions, 30000)

    selected_ids = {
        r["intervention_id"] for r in result["recommendations"]
    }

    assert selected_ids == {1, 2}


def test_incompatible_group_selects_at_most_one():
    interventions = [
        make_intervention(1, 10000, 30, group="site_A"),
        make_intervention(2, 10000, 50, group="site_A"),
    ]

    result = optimize_interventions(interventions, 20000)

    selected_ids = {
        r["intervention_id"] for r in result["recommendations"]
    }

    assert selected_ids == {2}


def test_zero_budget_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        optimize_interventions([], 0)


def test_dependency_chain_selects_all_prerequisites():
    interventions = [
        make_intervention(1, 10000, 10),
        make_intervention(2, 10000, 20, dependency=1),
        make_intervention(3, 10000, 50, dependency=2),
    ]

    result = optimize_interventions(interventions, 30000)

    selected_ids = {
        r["intervention_id"] for r in result["recommendations"]
    }

    assert selected_ids == {1, 2, 3}
    assert result["total_cost"] == 30000
    assert result["total_benefit_score"] == 80
