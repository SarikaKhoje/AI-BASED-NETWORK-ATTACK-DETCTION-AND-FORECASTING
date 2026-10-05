import joblib
import pandas as pd
import numpy as np
import shap
import matplotlib.pyplot as plt


# ============================================================
# PATHS
# ============================================================

DATA_PATH = "data/detection_prepared.csv"
MODEL_PATH = "models/detection_model.pkl"
RESULT_PATH = "results/shap_global_importance.png"


# ============================================================
# LOAD ACTUAL DATA
# ============================================================

print("=" * 60)
print("SHAP GLOBAL FEATURE IMPORTANCE")
print("=" * 60)

df = pd.read_csv(DATA_PATH)

X = df.drop(columns=["Label"])
X = X.select_dtypes(include=["number"])

print("Total rows:", len(X))
print("Features:", X.shape[1])


# ============================================================
# LOAD ACTUAL RANDOM FOREST
# ============================================================

model = joblib.load(MODEL_PATH)

print("Random Forest model loaded.")


# ============================================================
# USE REAL DATA SAMPLE
# ============================================================

X_sample = X.sample(
    n=1000,
    random_state=42
)

print("Real flows used for SHAP:", len(X_sample))


# ============================================================
# CREATE SHAP EXPLAINER
# ============================================================

print("\nCalculating SHAP values...")

explainer = shap.TreeExplainer(model)

shap_values = explainer.shap_values(X_sample)

print("SHAP values calculated.")


# ============================================================
# CALCULATE GLOBAL IMPORTANCE
# ============================================================

print("\nCalculating global feature importance...")

if isinstance(shap_values, list):

    # Older SHAP versions
    shap_array = np.stack(shap_values)

    importance = np.mean(
        np.abs(shap_array),
        axis=(0, 1)
    )

else:

    # Newer SHAP versions
    if shap_values.ndim == 3:

        importance = np.mean(
            np.abs(shap_values),
            axis=(0, 2)
        )

    else:

        importance = np.mean(
            np.abs(shap_values),
            axis=0
        )


# ============================================================
# CREATE IMPORTANCE TABLE
# ============================================================

importance_df = pd.DataFrame({
    "Feature": X_sample.columns,
    "SHAP Importance": importance
})

importance_df = importance_df.sort_values(
    by="SHAP Importance",
    ascending=False
)


# ============================================================
# PRINT TOP FEATURES
# ============================================================

print("\nTop 15 SHAP features:")
print("-" * 50)

print(
    importance_df.head(15).to_string(index=False)
)


# ============================================================
# PLOT TOP 15 FEATURES
# ============================================================

top_features = importance_df.head(15)

top_features = top_features.sort_values(
    by="SHAP Importance"
)

plt.figure(figsize=(10, 7))

plt.barh(
    top_features["Feature"],
    top_features["SHAP Importance"]
)

plt.xlabel("Mean Absolute SHAP Value")
plt.ylabel("Network Feature")

plt.title(
    "Global SHAP Feature Importance - Network Attack Detection"
)

plt.tight_layout()

plt.savefig(
    RESULT_PATH,
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# COMPLETED
# ============================================================

print("\nSHAP global importance saved:")
print(RESULT_PATH)

print("\n" + "=" * 60)
print("SHAP ANALYSIS COMPLETED")
print("=" * 60)