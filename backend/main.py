"""
AI-Based Network Attack Detection and Forecasting
FastAPI Backend

Run:
    python -m uvicorn backend.main:app --reload
"""

import pandas as pd
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from backend import model_loader
from backend.schemas import (
    DetectRequest, DetectResponse,
    ForecastResponse,
    RiskRequest, RiskResponse,
    ExplainRequest, ExplainResponse,
    DashboardResponse,
)
from backend.detection_api import run_detection
from backend.forecast_api  import run_forecast, get_all_windows
from backend.risk_api      import run_risk
from backend.shap_api      import run_explain
from backend.live_pipeline import process_csv_bytes, get_live_result


# ── Startup: load models once ──────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    model_loader.load_all_models()
    yield


app = FastAPI(
    title="AI Network Security API",
    description=(
        "Detection: Random Forest (84 features) | "
        "Forecasting: Gradient Boosting Regressor (17 features) | "
        "Risk: Rule-Based Engine | "
        "Explanation: SHAP TreeExplainer"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS for React dev server ──────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── GET / ──────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "AI Network Security API is running"}


# ── GET /health ────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "OK",
        "detection_model":   model_loader.detection_model  is not None,
        "forecasting_model": model_loader.forecast_model   is not None,
        "risk_engine":       True,
    }


# ── POST /detect ───────────────────────────────────────────
@app.post("/detect", response_model=DetectResponse)
def detect(request: DetectRequest):
    """
    Classify a single network flow using the trained Random Forest.
    Input: dict of raw network-flow features (missing ones default to 0).
    """
    return run_detection(request)


# ── GET /forecast ──────────────────────────────────────────
@app.get("/forecast", response_model=ForecastResponse)
def forecast(window_index: int = Query(default=-1, description="Row index in forecasting dataset (-1 = latest)")):
    """
    Predict attack count for the next 5-minute window.
    Uses the trained Gradient Boosting Regressor on CIC-IDS2017 prepared data.
    Data source: Demo / Historical CIC-IDS2017 Data
    """
    return run_forecast(window_index)


# ── POST /risk ─────────────────────────────────────────────
@app.post("/risk", response_model=RiskResponse)
def risk(request: RiskRequest):
    """
    Rule-Based Risk Assessment Engine.
    Combines current attack count, forecast, ratio, and attack type
    into a risk score (0-100) and level (LOW/MEDIUM/HIGH/CRITICAL).
    """
    return run_risk(request)


# ── POST /explain ──────────────────────────────────────────
@app.post("/explain", response_model=ExplainResponse)
def explain(request: ExplainRequest):
    """
    SHAP explanation for a single network flow.
    Answers: 'Why did the Random Forest classify this flow this way?'
    """
    return run_explain(request)


# ── POST /upload-csv ──────────────────────────────────────
@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CICFlowMeter-generated CSV.
    Runs the full pipeline: Random Forest → Aggregation → Forecast → Risk → SHAP.
    Dashboard updates automatically after this call.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    try:
        result = process_csv_bytes(content, file.filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /live-status ───────────────────────────────────────
@app.get("/live-status")
def live_status():
    """
    Returns the latest result from the last uploaded CSV.
    React dashboard polls this to auto-update.
    """
    result, updated_at = get_live_result()
    if result is None:
        return {"available": False, "updated_at": None, "data": None}
    return {"available": True, "updated_at": updated_at, "data": result}


# ── GET /dashboard ─────────────────────────────────────────
@app.get("/dashboard", response_model=DashboardResponse)
def dashboard(mode: str = Query(default="demo", description="'demo' or 'live'")):
    """
    Combined endpoint for the React dashboard.
    Returns detection, forecast, risk, SHAP, and chart data in one call.
    Demo mode uses actual CIC-IDS2017 prepared data and trained models.
    """
    # ── 1. Forecast (latest window) ────────────────────────
    forecast_result = run_forecast(-1)

    # ── 2. Detection (last flow from detection CSV) ────────
    try:
        df = pd.read_csv("data/detection_prepared.csv", nrows=5000)
        # Pick a representative attack flow for demo
        attack_rows = df[df["Label"] != "BENIGN"]
        sample_row  = attack_rows.iloc[0] if not attack_rows.empty else df.iloc[-1]
        features_dict = {
            col: sample_row[col]
            for col in model_loader.detection_features
            if col in sample_row.index
        }
        detect_result = run_detection(DetectRequest(features=features_dict))
    except Exception as e:
        detect_result = None

    # ── 3. Risk ────────────────────────────────────────────
    if detect_result and forecast_result:
        risk_result = run_risk(RiskRequest(
            current_attack_count=forecast_result.current_attack_count,
            predicted_attack_count=forecast_result.predicted_attack_count,
            attack_ratio=forecast_result.attack_ratio,
            attack_type=detect_result.attack_type if detect_result.is_attack else None,
        ))
    else:
        risk_result = None

    # ── 4. SHAP explanation ────────────────────────────────
    explain_result = None
    if detect_result and features_dict:
        try:
            explain_result = run_explain(ExplainRequest(features=features_dict))
        except Exception:
            explain_result = None

    # ── 5. Chart data (all windows) ───────────────────────
    all_windows = get_all_windows()

    # Recent 10 windows for the table
    recent = all_windows[-10:] if len(all_windows) >= 10 else all_windows

    return DashboardResponse(
        mode="DEMO — Historical CIC-IDS2017 Traffic" if mode == "demo" else "LIVE",
        detection=detect_result,
        forecast=forecast_result,
        risk=risk_result,
        explanation=explain_result,
        recent_windows=recent,
        attack_chart=all_windows,
    )
