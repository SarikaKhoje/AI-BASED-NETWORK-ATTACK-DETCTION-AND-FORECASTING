"""
SHAP explanation API.
Explains why the Random Forest classified a flow as a particular attack.
Uses shap.TreeExplainer — no retraining, no fake values.
"""

import numpy as np
import shap
from fastapi import HTTPException

from backend import model_loader
from backend.detection_api import _build_feature_df
from backend.schemas import ExplainRequest, ExplainResponse, SHAPFeature

# Cache the explainer so it is built only once
_explainer = None


def _get_explainer():
    global _explainer
    if _explainer is None:
        if model_loader.detection_model is None:
            raise HTTPException(status_code=503, detail="Detection model not loaded")
        _explainer = shap.TreeExplainer(model_loader.detection_model)
    return _explainer


def run_explain(request: ExplainRequest) -> ExplainResponse:
    model = model_loader.detection_model
    if model is None:
        raise HTTPException(status_code=503, detail="Detection model not loaded")

    X = _build_feature_df(request.features)

    # Prediction
    prediction    = model.predict(X)[0]
    probabilities = model.predict_proba(X)[0]
    class_index   = list(model.classes_).index(prediction)
    confidence    = float(probabilities[class_index])

    # SHAP values
    explainer   = _get_explainer()
    shap_values = explainer.shap_values(X)

    # Handle both old (list) and new (ndarray) SHAP formats
    if isinstance(shap_values, list):
        values = shap_values[class_index][0]
    else:
        if shap_values.ndim == 3:
            values = shap_values[0, :, class_index]
        else:
            values = shap_values[0]

    # Build top-10 feature list sorted by |SHAP|
    feature_names = model_loader.detection_features
    feature_vals  = X.iloc[0].values

    pairs = sorted(
        zip(feature_names, values, feature_vals),
        key=lambda t: abs(t[1]),
        reverse=True,
    )[:10]

    top_features = [
        SHAPFeature(
            feature=name,
            shap_value=round(float(sv), 6),
            feature_value=round(float(fv), 4),
        )
        for name, sv, fv in pairs
    ]

    return ExplainResponse(
        prediction=prediction,
        confidence=round(confidence, 4),
        top_features=top_features,
    )
