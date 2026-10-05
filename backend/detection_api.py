"""
Detection API logic.
Reuses the same preprocessing pipeline used during training.
Random Forest Classifier — 84 features.
"""

import numpy as np
import pandas as pd
from fastapi import HTTPException

from backend import model_loader
from backend.schemas import DetectRequest, DetectResponse


def _build_feature_df(raw: dict) -> pd.DataFrame:
    """
    Build a single-row DataFrame with exactly the 84 detection features
    in the correct order, filling missing ones with 0.
    """
    features = model_loader.detection_features
    row = {}
    for feat in features:
        val = raw.get(feat, 0)
        try:
            val = float(val)
        except (TypeError, ValueError):
            val = 0.0
        if np.isinf(val) or np.isnan(val):
            val = 0.0
        row[feat] = val
    return pd.DataFrame([row])[features]


def run_detection(request: DetectRequest) -> DetectResponse:
    model = model_loader.detection_model
    if model is None:
        raise HTTPException(status_code=503, detail="Detection model not loaded")

    X = _build_feature_df(request.features)

    prediction   = model.predict(X)[0]
    probabilities = model.predict_proba(X)[0]
    class_index  = list(model.classes_).index(prediction)
    confidence   = float(probabilities[class_index])

    return DetectResponse(
        prediction=prediction,
        confidence=round(confidence, 4),
        attack_type=prediction,
        is_attack=(prediction != "BENIGN"),
    )
