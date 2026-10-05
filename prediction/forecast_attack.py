import pandas as pd
import joblib
import json


# ============================================================
# FILE PATHS
# ============================================================

DATA_PATH = "data/forecasting_prepared.csv"
MODEL_PATH = "models/forecasting_model.pkl"
FEATURE_PATH = "models/forecasting_features.json"


print("=" * 60)
print("AI NETWORK ATTACK FORECASTING")
print("=" * 60)


# ============================================================
# 1. LOAD PREPARED FORECASTING DATA
# ============================================================

df = pd.read_csv(DATA_PATH)

print()
print("Dataset shape:", df.shape)


# ============================================================
# 2. CONVERT DATETIME
# ============================================================

df["parsed_datetime"] = pd.to_datetime(
    df["parsed_datetime"]
)


# ============================================================
# 3. SORT BY TIME
# ============================================================

df = (
    df
    .sort_values("parsed_datetime")
    .reset_index(drop=True)
)


# ============================================================
# 4. LOAD TRAINED FORECASTING MODEL
# ============================================================

model = joblib.load(
    MODEL_PATH
)

print("Forecasting model loaded successfully.")


# ============================================================
# 5. LOAD FEATURE NAMES
# ============================================================

with open(FEATURE_PATH, "r") as file:

    features = json.load(file)


print(
    "Number of features:",
    len(features)
)


# ============================================================
# 6. CHECK REQUIRED FEATURES
# ============================================================

missing_features = [
    feature
    for feature in features
    if feature not in df.columns
]

if missing_features:

    print()
    print("ERROR: Missing features:")

    for feature in missing_features:
        print("-", feature)

    raise ValueError(
        "Required forecasting features are missing."
    )


# ============================================================
# 7. CHECK DATASET
# ============================================================

if df.empty:

    raise ValueError(
        "Forecasting dataset is empty."
    )


# ============================================================
# 8. GET LATEST 5-MINUTE WINDOW
# ============================================================

latest = df.iloc[-1]


print()
print("=" * 60)
print("LATEST NETWORK WINDOW")
print("=" * 60)

print(
    "Current time:",
    latest["parsed_datetime"]
)

print(
    "Current attack flows:",
    int(latest["attack_flows"])
)

print(
    "Current normal flows:",
    int(latest["normal_flows"])
)


# ============================================================
# 9. PREPARE INPUT FOR MODEL
# ============================================================

X_latest = (
    latest[features]
    .to_frame()
    .T
)


# ============================================================
# 10. FORECAST NEXT 5-MINUTE ATTACK COUNT
# ============================================================

prediction = model.predict(
    X_latest
)[0]


# Attack count cannot be negative
prediction = max(
    0,
    prediction
)


# ============================================================
# 11. CALCULATE NEXT WINDOW TIME
# ============================================================

next_window_start = (
    latest["parsed_datetime"]
    + pd.Timedelta(minutes=5)
)

next_window_end = (
    next_window_start
    + pd.Timedelta(minutes=5)
)


# ============================================================
# 12. DETERMINE RISK LEVEL
# ============================================================

if prediction < 1000:

    risk = "LOW"

elif prediction < 10000:

    risk = "MEDIUM"

elif prediction < 50000:

    risk = "HIGH"

else:

    risk = "CRITICAL"


# ============================================================
# 13. DISPLAY FORECAST
# ============================================================

print()
print("=" * 60)
print("FORECAST RESULT")
print("=" * 60)

print(
    "Current window:",
    latest["parsed_datetime"]
)

print(
    "Current attack flows:",
    int(latest["attack_flows"])
)

print(
    "Forecast window:",
    next_window_start,
    "to",
    next_window_end
)

print(
    "Predicted attack count:",
    round(prediction)
)

print(
    "Forecasted risk level:",
    risk
)


# ============================================================
# 14. FINAL MESSAGE
# ============================================================

print()
print("=" * 60)
print("FORECAST COMPLETED")
print("=" * 60)

print(
    "The model predicts approximately",
    round(prediction),
    "attack flows in the next 5-minute window."
)

print(
    "Forecasted risk:",
    risk
)

print("=" * 60)