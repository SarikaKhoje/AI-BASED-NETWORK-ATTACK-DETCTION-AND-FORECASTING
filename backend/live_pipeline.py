"""
Live Pipeline — processes a CICFlowMeter-generated CSV through the full system.

Flow:
  Uploaded CSV (84 flow features)
    → Random Forest detection (per flow)
    → 5-minute window aggregation
    → Gradient Boosting forecast (next window)
    → Rule-Based Risk Engine
    → SHAP explanation on demand (on most recent attack flow)
"""

import io
import numpy as np
import pandas as pd
from datetime import datetime

from backend import model_loader
from backend.schemas import ExplainRequest, RiskRequest
from backend.risk_api import run_risk
from backend.shap_api import run_explain


# ── Shared state: last live result ────────────────────────
_live_result: dict = None
_live_updated_at: str = None
_live_explanation_features: dict = None
_live_explanation = None


def get_live_result():
    return _live_result, _live_updated_at


def get_live_explanation():
    global _live_explanation

    if _live_explanation_features is None:
        raise ValueError("Upload a CSV before requesting its explanation")
    if _live_explanation is None:
        _live_explanation = run_explain(
            ExplainRequest(features=_live_explanation_features)
        )
        if _live_result is not None:
            _live_result["explanation"] = _live_explanation.model_dump()
    return _live_explanation


def process_csv_bytes(file_bytes: bytes, filename: str) -> dict:
    """
    Process an uploaded CICFlowMeter CSV and return dashboard results.
    SHAP is calculated separately so the main results are available sooner.
    """
    global _live_result, _live_updated_at
    global _live_explanation_features, _live_explanation

    detection_model  = model_loader.detection_model
    forecast_model   = model_loader.forecast_model
    forecast_features = model_loader.forecast_features
    detection_features = model_loader.detection_features

    if detection_model is None or forecast_model is None:
        raise RuntimeError("Models not loaded")

    # ── 1. Load CSV ────────────────────────────────────────
    df = pd.read_csv(io.BytesIO(file_bytes))
    df.columns = df.columns.str.strip()

    if df.empty:
        raise ValueError("Uploaded CSV is empty")

    # ── 2. Clean ───────────────────────────────────────────
    df = df.replace([np.inf, -np.inf], np.nan)

    # ── 3. Parse timestamp if present ─────────────────────
    has_timestamp = "Timestamp" in df.columns
    if has_timestamp:
        df["parsed_datetime"] = pd.to_datetime(
            df["Timestamp"], errors="coerce"
        )
        df = df.dropna(subset=["parsed_datetime"])
        if df.empty:
            raise ValueError("No rows contain a valid timestamp")
    else:
        # Assign synthetic timestamps starting from now
        base = pd.Timestamp.now().floor("5min")
        df["parsed_datetime"] = [
            base + pd.Timedelta(seconds=i) for i in range(len(df))
        ]

    df = df.sort_values("parsed_datetime").reset_index(drop=True)

    # ── 4. Build detection feature matrix ─────────────────
    for feat in detection_features:
        if feat not in df.columns:
            df[feat] = 0.0
        else:
            df[feat] = pd.to_numeric(df[feat], errors="coerce").fillna(0)

    X = df[detection_features].fillna(0)

    # ── 5. Run Random Forest on every flow ────────────────
    probabilities = detection_model.predict_proba(X)
    predictions   = detection_model.classes_[probabilities.argmax(axis=1)]
    confidences   = probabilities.max(axis=1)

    df["rf_prediction"] = predictions
    df["rf_confidence"] = confidences
    df["is_attack"]     = predictions != "BENIGN"

    total_flows  = len(df)
    attack_flows = int(df["is_attack"].sum())
    normal_flows = total_flows - attack_flows
    attack_ratio = round(attack_flows / total_flows, 4) if total_flows > 0 else 0.0

    # ── 6. Most common attack type ────────────────────────
    attack_only = df[df["is_attack"]]
    if not attack_only.empty:
        dominant_attack = attack_only["rf_prediction"].value_counts().idxmax()
        dominant_conf   = float(
            attack_only[attack_only["rf_prediction"] == dominant_attack]["rf_confidence"].mean()
        )
    else:
        dominant_attack = "BENIGN"
        dominant_conf   = float(df["rf_confidence"].mean())

    # ── 7. 5-minute window aggregation ────────────────────
    df["time_window"] = df["parsed_datetime"].dt.floor("5min")

    # Build aggregation dict only for columns that exist
    safe_agg = {}
    col_map = {
        "total_flows":       ("parsed_datetime", "count"),
        "attack_flows":      ("is_attack",       "sum"),
        "avg_packet_rate":   ("Flow Packets/s",  "mean"),
        "avg_byte_rate":     ("Flow Bytes/s",    "mean"),
        "avg_flow_duration": ("Flow Duration",   "mean"),
        "syn_count":         ("SYN Flag Count",  "sum"),
        "rst_count":         ("RST Flag Count",  "sum"),
    }
    for out_col, (src_col, func) in col_map.items():
        if src_col in df.columns:
            safe_agg[out_col] = (src_col, func)
        else:
            safe_agg[out_col] = ("is_attack", "count")

    # Unique IPs
    if "Src IP dec" in df.columns:
        safe_agg["unique_src_ip"] = ("Src IP dec", "nunique")
    if "Dst IP dec" in df.columns:
        safe_agg["unique_dst_ip"] = ("Dst IP dec", "nunique")

    windows = df.groupby("time_window").agg(**safe_agg).reset_index()
    windows.rename(columns={"time_window": "parsed_datetime"}, inplace=True)

    windows["normal_flows"] = windows["total_flows"] - windows["attack_flows"]
    windows["attack_ratio"] = np.where(
        windows["total_flows"] > 0,
        windows["attack_flows"] / windows["total_flows"], 0
    )

    # Fill missing columns with 0
    for col in ["unique_src_ip", "unique_dst_ip"]:
        if col not in windows.columns:
            windows[col] = 0

    # ── 8. Lag + rolling features ─────────────────────────
    windows["attack_count_lag_1"] = windows["attack_flows"].shift(1).fillna(0)
    windows["attack_count_lag_2"] = windows["attack_flows"].shift(2).fillna(0)
    windows["attack_count_lag_3"] = windows["attack_flows"].shift(3).fillna(0)

    prev = windows["attack_flows"].shift(1)
    windows["rolling_mean_3"] = prev.rolling(3, min_periods=1).mean().fillna(0)
    windows["rolling_std_3"]  = prev.rolling(3, min_periods=1).std().fillna(0)
    windows["rolling_max_3"]  = prev.rolling(3, min_periods=1).max().fillna(0)

    windows = windows.replace([np.inf, -np.inf], np.nan).fillna(0)

    # ── 9. Forecast all windows in one model call ─────────
    latest = windows.iloc[-1]
    X_fore = windows[forecast_features].astype(float)
    forecast_predictions = np.maximum(
        0, np.rint(forecast_model.predict(X_fore))
    ).astype(int)
    predicted_attack_count = int(forecast_predictions[-1])

    window_start = latest["parsed_datetime"] + pd.Timedelta(minutes=5)
    window_end   = window_start + pd.Timedelta(minutes=5)

    def forecast_risk_label(n):
        if n < 1000:   return "LOW"
        if n < 10000:  return "MEDIUM"
        if n < 50000:  return "HIGH"
        return "CRITICAL"

    # ── 10. Risk Engine ───────────────────────────────────
    risk_result = run_risk(RiskRequest(
        current_attack_count=int(latest["attack_flows"]),
        predicted_attack_count=predicted_attack_count,
        attack_ratio=float(latest["attack_ratio"]),
        attack_type=dominant_attack if dominant_attack != "BENIGN" else None,
    ))

    # ── 11. Chart data ────────────────────────────────────
    attack_chart = []
    for (_, row), pred_w in zip(windows.iterrows(), forecast_predictions):
        attack_chart.append({
            "time":          str(row["parsed_datetime"]),
            "attack_flows":  int(row["attack_flows"]),
            "normal_flows":  int(row["normal_flows"]),
            "predicted_next": int(pred_w),
            "attack_ratio":  round(float(row["attack_ratio"]), 4),
        })

    recent_windows = attack_chart[-10:]

    # ── 12. Build response ────────────────────────────────
    result = {
        "mode": f"LIVE — {filename}",
        "detection": {
            "prediction":   dominant_attack,
            "confidence":   round(dominant_conf, 4),
            "attack_type":  dominant_attack,
            "is_attack":    dominant_attack != "BENIGN",
        },
        "forecast": {
            "forecast_window_start":   str(window_start),
            "forecast_window_end":     str(window_end),
            "predicted_attack_count":  predicted_attack_count,
            "current_attack_count":    int(latest["attack_flows"]),
            "attack_ratio":            round(float(latest["attack_ratio"]), 4),
            "forecast_risk_label":     forecast_risk_label(predicted_attack_count),
            "data_source":             f"Live upload: {filename}",
        },
        "risk": {
            "risk_score":  risk_result.risk_score,
            "risk_level":  risk_result.risk_level,
            "engine":      "Rule-Based Risk Assessment Engine",
        },
        "explanation": None,
        "recent_windows": recent_windows,
        "attack_chart":   attack_chart,
        "summary": {
            "total_flows":   total_flows,
            "attack_flows":  attack_flows,
            "normal_flows":  normal_flows,
            "attack_ratio":  attack_ratio,
            "total_windows": len(windows),
            "filename":      filename,
        },
    }

    if not attack_only.empty:
        shap_row = attack_only.iloc[-1]
    else:
        shap_row = df.iloc[-1]
    explanation_features = {
        col: float(shap_row[col])
        for col in detection_features
        if col in shap_row.index
    }

    _live_explanation_features = explanation_features
    _live_explanation = None
    _live_result = result
    _live_updated_at = datetime.now().isoformat()
    return result
