"""
Risk API logic.
Delegates entirely to the existing Rule-Based Risk Assessment Engine.
risk/risk_engine.py — no ML, pure rule-based thresholds.
"""

from backend.schemas import RiskRequest, RiskResponse
from risk.risk_engine import calculate_risk


def run_risk(request: RiskRequest) -> RiskResponse:
    result = calculate_risk(
        current_attack_count=request.current_attack_count,
        predicted_attack_count=request.predicted_attack_count,
        attack_ratio=request.attack_ratio,
        attack_type=request.attack_type,
    )
    return RiskResponse(
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
    )
