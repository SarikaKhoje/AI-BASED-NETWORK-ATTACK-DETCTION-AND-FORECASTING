"""
Pydantic schemas for all API endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ── /detect ────────────────────────────────────────────────
class DetectRequest(BaseModel):
    features: Dict[str, Any]   # raw network-flow key/value pairs


class DetectResponse(BaseModel):
    prediction: str
    confidence: float
    attack_type: str
    is_attack: bool


# ── /risk ──────────────────────────────────────────────────
class RiskRequest(BaseModel):
    current_attack_count: int
    predicted_attack_count: int
    attack_ratio: float
    attack_type: Optional[str] = None


class RiskResponse(BaseModel):
    risk_score: int
    risk_level: str
    engine: str = "Rule-Based Risk Assessment Engine"


# ── /explain ───────────────────────────────────────────────
class ExplainRequest(BaseModel):
    features: Dict[str, Any]


class SHAPFeature(BaseModel):
    feature: str
    shap_value: float
    feature_value: float


class ExplainResponse(BaseModel):
    prediction: str
    confidence: float
    top_features: List[SHAPFeature]


# ── /forecast ──────────────────────────────────────────────
class ForecastResponse(BaseModel):
    forecast_window_start: str
    forecast_window_end: str
    predicted_attack_count: int
    current_attack_count: int
    attack_ratio: float
    forecast_risk_label: str
    data_source: str = "Demo / Historical CIC-IDS2017 Data"


# ── /dashboard ─────────────────────────────────────────────
class DashboardResponse(BaseModel):
    mode: str
    detection: Optional[DetectResponse]
    forecast: Optional[ForecastResponse]
    risk: Optional[RiskResponse]
    explanation: Optional[ExplainResponse]
    recent_windows: List[Dict[str, Any]]
    attack_chart: List[Dict[str, Any]]
