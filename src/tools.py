"""
Credit Analyst Agent — Mock Tools

Applicant schema and the mock tool functions: DTI/DSCR/LTV calculators
and the mock credit bureau pull.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Applicant:
    name: str
    monthly_income: float
    monthly_debt_payments: float          # existing debt obligations
    requested_loan_amount: float
    loan_purpose: str
    collateral_value: Optional[float]     # None for unsecured
    annual_net_operating_income: Optional[float] = None  # for DSCR (commercial)
    annual_debt_service: Optional[float] = None          # for DSCR
    employment_years: float = 0.0
    late_payments_last_2y: int = 0
    existing_defaults: int = 0


def calc_dti(applicant: Applicant) -> float:
    """Debt-to-Income ratio (%). Lower is better. Returns inf for commercial
    applicants (monthly_income == 0), where DTI doesn't apply — see DSCR."""
    if applicant.monthly_income <= 0:
        return float("inf")
    return round((applicant.monthly_debt_payments / applicant.monthly_income) * 100, 2)


def calc_dscr(applicant: Applicant) -> Optional[float]:
    """Debt Service Coverage Ratio — commercial loans only. >1.0 means income covers debt."""
    if not applicant.annual_net_operating_income or not applicant.annual_debt_service:
        return None
    if applicant.annual_debt_service <= 0:
        return None
    return round(applicant.annual_net_operating_income / applicant.annual_debt_service, 2)


def calc_ltv(applicant: Applicant) -> Optional[float]:
    """Loan-to-Value ratio (%) — only meaningful when collateral exists."""
    if not applicant.collateral_value or applicant.collateral_value <= 0:
        return None
    return round((applicant.requested_loan_amount / applicant.collateral_value) * 100, 2)


def mock_credit_bureau_pull(applicant: Applicant) -> dict:
    """Mock credit bureau API call (stands in for Equifax/TransUnion/etc.)."""
    base_score = 720
    base_score -= applicant.late_payments_last_2y * 15
    base_score -= applicant.existing_defaults * 100
    base_score += min(applicant.employment_years, 10) * 3
    score = max(300, min(850, round(base_score)))

    if score >= 740:
        band = "excellent"
    elif score >= 670:
        band = "good"
    elif score >= 580:
        band = "fair"
    else:
        band = "poor"

    return {
        "credit_score": score,
        "band": band,
        "late_payments_last_2y": applicant.late_payments_last_2y,
        "existing_defaults": applicant.existing_defaults,
        "open_tradelines": 3 + applicant.existing_defaults,
    }