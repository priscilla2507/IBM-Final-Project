
from unittest.mock import MagicMock, patch

import pytest

from app.services.optimization_db_service import run_and_save_optimization


def test_database_failure_rolls_back():
    db = MagicMock()

    # Simulate failure when committing the optimization run.
    db.commit.side_effect = RuntimeError("Simulated database failure")

    with patch(
        "app.services.optimization_db_service.optimize_interventions",
        return_value={
            "total_cost": 10000,
            "total_benefit_score": 20,
            "recommendations": [],
        },
    ):
        with pytest.raises(RuntimeError, match="Simulated database failure"):
            run_and_save_optimization(db, 20000)

    db.rollback.assert_called_once()
