import pandas as pd
import joblib
import json

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# ============================================================
# FILE PATHS
# ============================================================

DATA_PATH = "data/forecasting_prepared.csv"
MODEL_PATH = "models/forecasting_model.pkl"
FEATURE_PATH = "models/forecasting_features.json"


print("=" * 60)
print("FORECASTING MODEL TRAINING")
print("=" * 60)


# ============================================================
# LOAD DATASET
# ============================================================

df = pd.read_csv(DATA_PATH)

print()
print("Dataset shape:", df.shape)


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "parsed_datetime",
    "total_flows",
    "attack_flows",
    "normal_flows",
    "avg_packet_rate",
    "avg_byte_rate",
    "avg_flow_duration",
    "syn_count",
    "rst_count",
    "unique_src_ip",
    "unique_dst_ip",
    "next_window_attack_count",
    "attack_count_lag_1",
    "attack_count_lag_2",
    "attack_count_lag_3",
    "attack_ratio",
    "rolling_mean_3",
    "rolling_std_3",
    "rolling_max_3"
]


missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]


if missing_columns:

    print()
    print("ERROR: Missing columns:")

    for column in missing_columns:
        print("-", column)

    raise ValueError(
        "Forecasting dataset is missing required columns."
    )


# ============================================================
# DATETIME CONVERSION
# ============================================================

df["parsed_datetime"] = pd.to_datetime(
    df["parsed_datetime"]
)


# ============================================================
# SORT CHRONOLOGICALLY
# ============================================================

df = (
    df
    .sort_values("parsed_datetime")
    .reset_index(drop=True)
)


# ============================================================
# FEATURES
# ============================================================

features = [
    "total_flows",
    "attack_flows",
    "normal_flows",

    "avg_packet_rate",
    "avg_byte_rate",
    "avg_flow_duration",

    "syn_count",
    "rst_count",

    "unique_src_ip",
    "unique_dst_ip",

    "attack_count_lag_1",
    "attack_count_lag_2",
    "attack_count_lag_3",

    "attack_ratio",

    "rolling_mean_3",
    "rolling_std_3",
    "rolling_max_3"
]


# ============================================================
# TARGET
# ============================================================

target = "next_window_attack_count"


X = df[features]
y = df[target]


print()
print("Number of features:", len(features))
print("Target:", target)


# ============================================================
# CHRONOLOGICAL TRAIN-TEST SPLIT
# ============================================================

split_index = int(len(df) * 0.80)


X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]


print()
print("=" * 60)
print("CHRONOLOGICAL DATA SPLIT")
print("=" * 60)

print("Total samples:", len(df))
print("Training samples:", len(X_train))
print("Testing samples:", len(X_test))

print(
    "Training period:",
    df["parsed_datetime"].iloc[0],
    "to",
    df["parsed_datetime"].iloc[split_index - 1]
)

print(
    "Testing period:",
    df["parsed_datetime"].iloc[split_index],
    "to",
    df["parsed_datetime"].iloc[-1]
)


# ============================================================
# CREATE MODEL
# ============================================================

model = GradientBoostingRegressor(
    n_estimators=100,
    learning_rate=0.05,
    max_depth=3,
    random_state=42
)


# ============================================================
# TRAIN MODEL
# ============================================================

print()
print("=" * 60)
print("TRAINING GRADIENT BOOSTING REGRESSOR")
print("=" * 60)

model.fit(
    X_train,
    y_train
)

print()
print("Training completed.")


# ============================================================
# PREDICTION
# ============================================================

y_pred = model.predict(X_test)


# ============================================================
# EVALUATION
# ============================================================

mae = mean_absolute_error(
    y_test,
    y_pred
)

mse = mean_squared_error(
    y_test,
    y_pred
)

rmse = mse ** 0.5

r2 = r2_score(
    y_test,
    y_pred
)


print()
print("=" * 60)
print("FORECASTING RESULTS")
print("=" * 60)

print("MAE :", round(mae, 2))
print("RMSE:", round(rmse, 2))
print("R²  :", round(r2, 4))


# ============================================================
# ACTUAL VS PREDICTED
# ============================================================

results = pd.DataFrame({

    "parsed_datetime":
        df.iloc[split_index:]["parsed_datetime"].values,

    "actual_attack_count":
        y_test.values,

    "predicted_attack_count":
        y_pred

})


print()
print("=" * 60)
print("ACTUAL VS PREDICTED")
print("=" * 60)

print(
    results.to_string(index=False)
)


# ============================================================
# SAVE MODEL
# ============================================================

joblib.dump(
    model,
    MODEL_PATH
)


# ============================================================
# SAVE FEATURE NAMES
# ============================================================

with open(
    FEATURE_PATH,
    "w"
) as file:

    json.dump(
        features,
        file,
        indent=4
    )


# ============================================================
# COMPLETED
# ============================================================

print()
print("=" * 60)
print("FILES SAVED")
print("=" * 60)

print("Model:", MODEL_PATH)
print("Features:", FEATURE_PATH)

print()
print("=" * 60)
print("FORECASTING MODEL TRAINING COMPLETED")
print("=" * 60)