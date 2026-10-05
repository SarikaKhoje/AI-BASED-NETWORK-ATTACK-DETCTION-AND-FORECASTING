"""
Forecast API logic.
Uses forecasting_prepared.csv (CIC-IDS2017 historical windows).
Gradient Boosting Regressor — 17 features from forecasting_features.json.
"""

import pandas as pd
from fastapi import HTTPException

from backend import model_loader
from backend.schemas import ForecastResponse

FORECAST_DATA_PATH = "data/forecasting_prepared.csv"

# Cached dataframe — loaded once
_forecast_df: pd.DataFrame = None


def _get_forecast_df() -> pd.DataFrame:
    global _forecast_df
    if _forecast_df is None:
        _forecast_df = pd.read_csv(FORECAST_DATA_PATH, parse_dates=["parsed_datetime"])
        _forecast_df = _forecast_df.sort_values("parsed_datetime").reset_index(drop=True)
    return _forecast_df


def _forecast_risk_label(count: int) -> str:
    if count < 1000:
        return "LOW"
    elif count < 10000:
        return "MEDIUM"
    elif count < 50000:
        return "HIGH"
    return "CRITICAL"


def run_forecast(window_index: int = -1) -> ForecastResponse:
    model    = model_loader.forecast_model
    features = model_loader.forecast_features
    if model is None:
        raise HTTPException(status_code=503, detail="Forecasting model not loaded")

    df = _get_forecast_df()
    if df.empty:
        raise HTTPException(status_code=500, detail="Forecasting dataset is empty")

    # Clamp index
    idx = window_index if window_index >= 0 else len(df) - 1
    idx = max(0, min(idx, len(df) - 1))

    row = df.iloc[idx]

    # Verify all 17 features exist
    missing = [f for f in features if f not in df.columns]
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing forecasting features: {missing}"
        )

    X = row[features].to_frame().T.astype(float)
    raw_pred = float(model.predict(X)[0])
    predicted = max(0, int(round(raw_pred)))

    window_start = row["parsed_datetime"] + pd.Timedelta(minutes=5)
    window_end   = window_start + pd.Timedelta(minutes=5)

    return ForecastResponse(
        forecast_window_start=str(window_start),
        forecast_window_end=str(window_end),
        predicted_attack_count=predicted,
        current_attack_count=int(row["attack_flows"]),
        attack_ratio=round(float(row["attack_ratio"]), 4),
        forecast_risk_label=_forecast_risk_label(predicted),
    )


def get_all_windows() -> list:
    """Return all time windows for chart rendering."""
    df = _get_forecast_df()
    features = model_loader.forecast_features
    if features is None:
        return []

    records = []
    for _, row in df.iterrows():
        X = row[features].to_frame().T.astype(float)
        pred = max(0, int(round(float(model_loader.forecast_model.predict(X)[0]))))
        records.append({
            "time": str(row["parsed_datetime"]),
            "attack_flows": int(row["attack_flows"]),
            "normal_flows": int(row["normal_flows"]),
            "predicted_next": pred,
            "attack_ratio": round(float(row["attack_ratio"]), 4),
        })
    return records
