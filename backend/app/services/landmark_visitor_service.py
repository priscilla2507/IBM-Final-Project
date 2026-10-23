
from typing import Optional


def estimate_daily_visitors(
    annual_visitors: Optional[int],
    source: Optional[str] = None,
    reporting_year: Optional[int] = None,
) -> dict:
    """
    Estimate average daily landmark visitors from an annual visitor count.

    This is an annual-average estimate, not actual daily footfall.
    It does not represent the number of people protected.
    """

    if annual_visitors is None:
        return {
            "estimated_daily_visitors": None,
            "annual_visitors": None,
            "source": source,
            "reporting_year": reporting_year,
            "method": "unavailable",
            "message": (
                "Reliable visitor statistics are unavailable "
                "for this landmark."
            ),
        }

    if isinstance(annual_visitors, bool) or annual_visitors < 0:
        raise ValueError(
            "Annual visitors must be a non-negative integer."
        )

    if not isinstance(annual_visitors, int):
        raise ValueError(
            "Annual visitors must be provided as an integer."
        )

    return {
        "estimated_daily_visitors": round(annual_visitors / 365),
        "annual_visitors": annual_visitors,
        "source": source,
        "reporting_year": reporting_year,
        "method": "annual_average",
        "message": (
            "Estimated average daily visitors calculated from "
            "the reported annual visitor count."
        ),
    }
