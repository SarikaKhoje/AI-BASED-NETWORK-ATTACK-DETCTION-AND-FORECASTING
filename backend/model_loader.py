"""
Loads all ML models once at startup.
Detection: Random Forest (84 features)
Forecasting: Gradient Boosting Regressor (17 features)
"""

import json
import joblib

# ── Paths ──────────────────────────────────────────────────
DETECTION_MODEL_PATH   = "models/detection_model.pkl"
DETECTION_FEATURE_PATH = "models/detection_features.json"
FORECAST_MODEL_PATH    = "models/forecasting_model.pkl"
FORECAST_FEATURE_PATH  = "models/forecasting_features.json"

# ── Loaded once ────────────────────────────────────────────
detection_model    = None
detection_features = None
forecast_model     = None
forecast_features  = None


def load_all_models():
    global detection_model, detection_features
    global forecast_model, forecast_features

    detection_model = joblib.load(DETECTION_MODEL_PATH)
    with open(DETECTION_FEATURE_PATH) as f:
        detection_features = json.load(f)

    forecast_model = joblib.load(FORECAST_MODEL_PATH)
    with open(FORECAST_FEATURE_PATH) as f:
        forecast_features = json.load(f)

    print(f"[model_loader] Detection model loaded  — {len(detection_features)} features")
    print(f"[model_loader] Forecasting model loaded — {len(forecast_features)} features")
