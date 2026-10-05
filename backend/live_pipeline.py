"""
Live Pipeline — processes a CICFlowMeter-generated CSV through the full system.

Flow:
  Uploaded CSV (84 flow features)
    → Random Forest detection (per flow)
    → 5-minute window aggregation
    → Gradient Boosting forecast (next window)
    → Rule-Based Risk Engine
    → SHAP explanation (on most recent attack flow)
"""

import io
import numpy as np
import pandas as pd
from datetime import datetime

from backend import model_loader
from backend.detection_api import _build_feature_df
from backend.schemas import DetectRequest, RiskRequest
from backend.detection_api import run_detection
from backend.risk_api import run_risk
from backend.shap_api import run_explain
from backend.schemas import ExplainRequest


# ── Shared state: last live result ────────────────────────
_live_result: dict = None
_live_updated_at: str = None


def get_live_result():
    return _live_result, _live_updated_at


def process_csv_bytes(file_bytes: bytes, filename: str) -> dict:
    """
    Full pipeline on an uploaded CICFlowMeter CSV.
    Returns the same structure as /dashboard so the frontend
    can update without any changes.
    """
    global _live_result, _live_updated_at

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
    else:
        # Assign synthetic timestamps starting from now
        base = pd.Timestamp.now().floor("5min")
        df["parsed_datetime"] = [
            base + pd.Timedelta(seconds=i) for i in range(len(df))
        ]

    df = df.sort_values("parsed_datetime").reset_index(drop=True)

    # ── 4. Build detection feature matrix ─────────────────
    X_rows = []
    for feat in detection_features:
        if feat not in df.columns:
            df[feat] = 0.0
        else:
            df[feat] = pd.to_numeric(df[feat], errors="coerce").fillna(0)

    X = df[detection_features].fillna(0)

    # ── 5. Run Random Forest on every flow ────────────────
    predictions   = detection_model.predict(X)
    probabilities = detection_model.predict_proba(X)
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

    agg_cols = {
        "total_flows":        ("parsed_datetime", "count"),
        "attack_flows":       ("is_attack",        "sum"),
        "avg_packet_rate":    ("Flow Packets/s",   "mean") if "Flow Packets/s"   in df.columns else ("is_attack", "count"),
        "avg_byte_rate":      ("Flow Bytes/s",     "mean") if "Flow Bytes/s"     in df.columns else ("is_attack", "count"),
        "avg_flow_duration":  ("Flow Duration",    "mean") if "Flow Duration"    in df.columns else ("is_attack", "count"),
        "syn_count":          ("SYN Flag Count",   "sum")  if "SYN Flag Count"   in df.columns else ("is_attack", "count"),
        "rst_count":          ("RST Flag Count",   "sum")  if "RST Flag Count"   in df.columns else ("is_attack", "count"),
    }

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

    # ── 9. Forecast on latest window ──────────────────────
    latest = windows.iloc[-1]
    X_fore = latest[forecast_features].to_frame().T.astype(float)
    raw_pred = float(forecast_model.predict(X_fore)[0])
    predicted_attack_count = max(0, int(round(raw_pred)))

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

    # ── 11. SHAP on most recent attack flow ───────────────
    explain_result = None
    try:
        if not attack_only.empty:
            shap_row = attack_only.iloc[-1]
        else:
            shap_row = df.iloc[-1]
        shap_feats = {
            col: float(shap_row[col])
            for col in detection_features
            if col in shap_row.index
        }
        explain_result = run_explain(ExplainRequest(features=shap_feats))
    except Exception:
        explain_result = None

    # ── 12. Chart data ────────────────────────────────────
    attack_chart = []
    for _, row in windows.iterrows():
        X_w = row[forecast_features].to_frame().T.astype(float)
        pred_w = max(0, int(round(float(forecast_model.predict(X_w)[0]))))
        attack_chart.append({
            "time":          str(row["parsed_datetime"]),
            "attack_flows":  int(row["attack_flows"]),
            "normal_flows":  int(row["normal_flows"]),
            "predicted_next": pred_w,
            "attack_ratio":  round(float(row["attack_ratio"]), 4),
        })

    recent_windows = attack_chart[-10:]

    # ── 13. Build response ────────────────────────────────
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
        "explanation": explain_result.model_dump() if explain_result else None,
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

    _live_result     = result
    _live_updated_at = datetime.now().isoformat()
    return result
