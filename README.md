# AI-Based Network Attack Detection and Forecasting

A college project that detects network attacks in real time, forecasts future attack activity,
assesses risk, and explains predictions — all through a React dashboard backed by FastAPI.

---

## Project Overview

This system answers three questions about network traffic:

| Question | Model | Answer |
|---|---|---|
| What is happening right now? | Random Forest Classifier | Attack type + confidence |
| What will happen next? | Gradient Boosting Regressor | Attack count in next 5 minutes |
| How serious is it? | Rule-Based Risk Engine | Risk score 0–100 + level |

SHAP (SHapley Additive exPlanations) explains **why** the Random Forest made each decision.

---

## How the Full System Works

```
Network Traffic (Wireshark/Zeek)
        ↓
    PCAP file
        ↓
  CICFlowMeter
        ↓
  CSV with 84 network-flow features
        ↓
  ┌─────────────────────────────────┐
  │     Random Forest Classifier    │  ← detection_model.pkl
  │     (84 features per flow)      │
  └─────────────────────────────────┘
        ↓
  Per-flow predictions (attack type)
        ↓
  5-minute window aggregation
        ↓
  ┌─────────────────────────────────┐
  │  Gradient Boosting Regressor    │  ← forecasting_model.pkl
  │  (17 aggregated features)       │
  └─────────────────────────────────┘
        ↓
  Predicted attack count (next 5 min)
        ↓
  ┌─────────────────────────────────┐
  │  Rule-Based Risk Engine         │  ← risk/risk_engine.py
  │  (score 0–100, LOW→CRITICAL)    │
  └─────────────────────────────────┘
        ↓
  SHAP Explanation
        ↓
  FastAPI  →  React Dashboard
```

---

## Project Structure

```
AI-Based Network Forecasting/
│
├── backend/                        # FastAPI backend
│   ├── __init__.py
│   ├── main.py                     # FastAPI app, all endpoints, CORS
│   ├── model_loader.py             # Loads both .pkl models once at startup
│   ├── schemas.py                  # Pydantic request/response shapes
│   ├── detection_api.py            # Random Forest detection logic
│   ├── forecast_api.py             # Gradient Boosting forecast logic
│   ├── risk_api.py                 # Calls risk_engine.py
│   ├── shap_api.py                 # SHAP explanation logic
│   └── live_pipeline.py            # Full pipeline for uploaded CSV
│
├── frontend/                       # React + Vite + Tailwind dashboard
│   └── src/
│       ├── services/api.js         # All fetch calls to FastAPI
│       ├── components/
│       │   ├── StatCard.jsx        # Summary stat cards
│       │   ├── AttackChart.jsx     # Attack/normal/forecast bar+line chart
│       │   └── SHAPChart.jsx       # SHAP horizontal bar chart
│       ├── pages/Dashboard.jsx     # Main dashboard page
│       ├── App.jsx
│       └── main.jsx
│
├── models/
│   ├── detection_model.pkl         # Trained Random Forest (84 features)
│   ├── detection_features.json     # Exact 84 feature names in order
│   ├── forecasting_model.pkl       # Trained Gradient Boosting (17 features)
│   └── forecasting_features.json   # Exact 17 feature names in order
│
├── data/
│   ├── detection_prepared.csv      # CIC-IDS2017 flow data (2M+ rows)
│   └── forecasting_prepared.csv    # 5-minute aggregated windows (40 rows)
│
├── preprocessing/
│   ├── detection_preprocessor.py   # Preprocessing used during training
│   └── forecasting_preprocessor.py # Aggregation pipeline
│
├── risk/
│   └── risk_engine.py              # Rule-based risk scoring
│
├── prediction/
│   ├── test_model.py               # Test detection model
│   ├── forecast_attack.py          # Test forecasting model
│   ├── explain_one_flow.py         # Test SHAP on one flow
│   └── test_shap.py                # Global SHAP importance
│
└── training/
    ├── train_detection.py          # How detection model was trained
    └── train_forecasting.py        # How forecasting model was trained
```

---

## File-by-File Explanation

### `backend/model_loader.py`
Loads both `.pkl` model files **once** when FastAPI starts.
Stores them as global variables so every API request reuses the same loaded model.
Never loads from disk on each request — this keeps the API fast.

### `backend/schemas.py`
Defines the exact shape of every API request and response using Pydantic.
For example, `DetectRequest` expects a dict of feature names → values.
`DetectResponse` always returns `prediction`, `confidence`, `attack_type`, `is_attack`.
If the wrong data is sent, FastAPI automatically returns a 422 error with a clear message.

### `backend/detection_api.py`
Takes raw network-flow feature values, builds a DataFrame with exactly the 84 features
in the correct order (from `detection_features.json`), fills missing features with 0,
replaces infinity/NaN with 0, then runs the Random Forest.
Returns the predicted class and confidence score.

### `backend/forecast_api.py`
Reads `forecasting_prepared.csv` (cached after first load).
Takes the latest 5-minute window row, selects exactly the 17 features from
`forecasting_features.json`, runs the Gradient Boosting Regressor, and returns
the predicted attack count for the next 5-minute window.

### `backend/risk_api.py`
A thin wrapper. Receives current attack count, predicted attack count, attack ratio,
and attack type. Passes them directly to `risk/risk_engine.py` and returns the result.
No ML involved — purely rule-based thresholds.

### `backend/shap_api.py`
Creates a `shap.TreeExplainer` from the Random Forest (cached after first use).
Runs SHAP on a single network flow and returns the top 10 features sorted by
absolute SHAP value. Positive SHAP = pushes toward attack. Negative = pushes toward benign.

### `backend/live_pipeline.py`
The most important file for live traffic. When a CICFlowMeter CSV is uploaded:
1. Reads and cleans the CSV
2. Runs Random Forest on **every single flow**
3. Aggregates flows into 5-minute windows
4. Calculates lag features and rolling statistics
5. Runs Gradient Boosting on the latest window
6. Runs the Risk Engine
7. Returns detection, forecast, risk, and chart results
8. Stores the result so `/live-status` can return it
9. Calculates SHAP separately through `/live-explanation` so it does not delay the main results

### `backend/main.py`
The FastAPI application. Registers all endpoints, configures CORS for React,
loads models at startup using `lifespan`, and wires each endpoint to its handler.

### `risk/risk_engine.py`
Pure rule-based scoring. No machine learning.
- Current attack count contributes up to 40 points
- Predicted attack count contributes up to 40 points
- Attack ratio contributes up to 20 points
- High-severity attack types (DDoS, DoS Hulk, Heartbleed) add 10 points
- Total score → LOW / MEDIUM / HIGH / CRITICAL

### `preprocessing/detection_preprocessor.py`
The exact same preprocessing used during model training.
Removes non-feature columns, replaces infinity with NaN, converts to numeric,
adds missing features as 0, selects exactly the 84 features in order.

### `frontend/src/services/api.js`
All HTTP calls to the FastAPI backend. Uses the Vite proxy so React calls `/api/...`
which gets forwarded to `http://127.0.0.1:8000/...`.

### `frontend/src/pages/Dashboard.jsx`
The main dashboard page. Handles:
- Demo/Live mode toggle
- CSV file upload with drag-and-drop
- Auto-polling `/live-status` every 5 seconds in Live mode
- Rendering all stat cards, charts, tables

### `frontend/src/components/AttackChart.jsx`
Recharts ComposedChart. Red bars = attack flows. Blue bars = normal flows.
Yellow line = forecasted next-window attack count.

### `frontend/src/components/SHAPChart.jsx`
Horizontal bar chart. Red bars = features pushing toward attack.
Blue bars = features pushing toward benign. Sorted by absolute SHAP value.

---

## ML Models

### Random Forest Classifier — Detection
- Trained on: CIC-IDS2017 dataset
- Input: 84 network-flow features
- Output: Attack class (BENIGN, DDoS, DoS Hulk, PortScan, Heartbleed, etc.)
- Performance: ~99.85% accuracy, precision, recall, F1
- File: `models/detection_model.pkl`

### Gradient Boosting Regressor — Forecasting
- Trained on: CIC-IDS2017 historical 5-minute windows
- Input: 17 aggregated features (attack counts, ratios, lags, rolling stats)
- Output: Predicted attack flow count for next 5-minute window
- Performance: MAE ≈ 15,357 | RMSE ≈ 29,398 | R² ≈ 0.2465
- Note: Small dataset (40 windows) — proof of concept
- File: `models/forecasting_model.pkl`

### Rule-Based Risk Engine — Risk Assessment
- Not ML — pure threshold rules
- Input: current count, predicted count, attack ratio, attack type
- Output: risk_score (0–100), risk_level (LOW/MEDIUM/HIGH/CRITICAL)
- File: `risk/risk_engine.py`

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API running message |
| GET | `/health` | Model load status |
| POST | `/detect` | Classify one network flow |
| GET | `/forecast` | Predict next 5-min attack count |
| POST | `/risk` | Calculate risk score and level |
| POST | `/explain` | SHAP explanation for one flow |
| POST | `/upload-csv` | Upload CICFlowMeter CSV → detection, forecast, risk, and charts |
| GET | `/live-status` | Latest result from uploaded CSV |
| GET | `/live-explanation` | Calculate SHAP explanation for the latest upload |
| GET | `/dashboard` | Combined response for React dashboard |
| GET | `/docs` | Swagger UI |

---

## Installation

### Requirements
- Python 3.9+
- Node.js 18+

### Python dependencies
```
pip install fastapi "uvicorn[standard]" python-multipart joblib pandas numpy scikit-learn shap
```

### Node dependencies
```
cd frontend
npm install
```

---

## Running the System

### Terminal 1 — Backend
```
cd "AI-Based Network Forecasting"
python -m uvicorn backend.main:app --reload --port 8000
```

### Terminal 2 — Frontend
```
cd "AI-Based Network Forecasting/frontend"
npm run dev
```

### Open browser
- Dashboard: `http://localhost:3000`
- API docs: `http://127.0.0.1:8000/docs`

---

## Two Modes

### DEMO MODE
Uses `data/detection_prepared.csv` and `data/forecasting_prepared.csv`.
Runs the actual trained models on real CIC-IDS2017 recorded traffic.
No fake predictions. Clearly labelled: **DEMO MODE — Historical CIC-IDS2017 Traffic**

### LIVE MODE
Upload a CICFlowMeter-generated CSV from real network traffic.
Detection, forecast, risk, and charts appear first; the SHAP explanation loads separately.
Clearly labelled: **LIVE MODE — filename.csv**

---

## Live Traffic — How to Use Real Network Data

To use real network traffic instead of the demo data:

**Step 1 — Capture traffic**
```
Open Wireshark → select your network interface → start capture
Let it run for a few minutes → File → Export Specified Packets → Save as .pcap
```

**Step 2 — Convert PCAP to CSV**
```
Download CICFlowMeter from: https://github.com/ahlashkari/CICFlowMeter
Run: java -jar CICFlowMeter.jar <your_capture.pcap> <output_folder>
This generates a .csv file with 84 network-flow features
```

**Step 3 — Upload to dashboard**
```
Go to http://localhost:3000
Click LIVE mode
Drag and drop the .csv file into the upload panel
Dashboard updates automatically with real predictions
```

---

## Data Flow Summary

```
[User uploads CSV]
      ↓
[FastAPI /upload-csv]
      ↓
[live_pipeline.py]
      ↓
[Random Forest on every flow] → attack type per flow
      ↓
[5-minute aggregation] → total_flows, attack_flows, attack_ratio, syn_count...
      ↓
[Lag + rolling features] → attack_count_lag_1/2/3, rolling_mean/std/max_3
      ↓
[Gradient Boosting on latest window] → predicted_attack_count
      ↓
[Risk Engine] → risk_score, risk_level
      ↓
[JSON response]
      ↓
[React Dashboard renders detection, forecast, risk, and chart results]
      ↓
[GET /live-explanation] → SHAP on latest attack flow → top 10 contributing features
```

---

## Common Errors and Fixes

| Error | Cause | Fix |
|---|---|---|
| `WinError 10013` | Port blocked by Windows/antivirus | Try `--port 8080` or `--port 9000` |
| `ModuleNotFoundError: fastapi` | Package not installed | `pip install fastapi uvicorn` |
| Dashboard shows no data | Backend not running | Start backend first, then frontend |
| Upload fails | Wrong file format | Must be CICFlowMeter `.csv` output |
| SHAP takes long | Explanation runs separately from upload results | Wait for the SHAP panel; the explainer caches after first use |
| `503 model not loaded` | Models not found | Run from project root directory |

---

## Viva Explanation (Short Version)

**What does this project do?**
It detects network attacks in real time, predicts future attack activity, and explains why each prediction was made.

**What models did you use?**
Random Forest for detection (84 features, 99.85% accuracy), Gradient Boosting for forecasting (17 features, predicts next 5-minute window), and a rule-based engine for risk scoring.

**What is SHAP?**
SHAP explains individual predictions. It shows which network features pushed the model toward classifying traffic as an attack and which pushed it toward benign.

**What dataset did you use?**
CIC-IDS2017 — a publicly available dataset from the Canadian Institute for Cybersecurity containing real recorded network attack traffic.

**Can it work on real traffic?**
Yes. Capture traffic with Wireshark, convert to CSV with CICFlowMeter, upload to the dashboard. The same trained models run on the real data.

**Did you retrain any models?**
No. The models were trained separately. The system only loads and uses the saved `.pkl` files.

---

## Dataset Reference

ISCX-IDS 2017 (CIC-IDS2017)
Canadian Institute for Cybersecurity
https://www.unb.ca/cic/datasets/ids-2017.html

Attacks included: DDoS, DoS Hulk, DoS GoldenEye, DoS Slowloris, DoS Slowhttptest,
PortScan, Heartbleed, Botnet, FTP-Patator, SSH-Patator, Web Attack (Brute Force, XSS, SQL Injection), Infiltration
