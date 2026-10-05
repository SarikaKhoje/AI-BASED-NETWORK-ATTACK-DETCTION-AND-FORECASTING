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
RESULT_PATH = "results/shap_one_flow.png"


# ============================================================
# LOAD DATA AND MODEL
# ============================================================

df = pd.read_csv(DATA_PATH)

X = df.drop(columns=["Label"])
X = X.select_dtypes(include=["number"])

model = joblib.load(MODEL_PATH)

print("=" * 60)
print("SHAP - INDIVIDUAL NETWORK FLOW")
print("=" * 60)


# ============================================================
# SELECT ONE REAL NETWORK FLOW
# ============================================================

flow = X.iloc[[0]]

print("Selected flow:", 0)


# ============================================================
# MODEL PREDICTION
# ============================================================

prediction = model.predict(flow)[0]

probabilities = model.predict_proba(flow)[0]

class_index = list(model.classes_).index(prediction)

confidence = probabilities[class_index] * 100

print("\nPrediction:", prediction)
print(f"Confidence: {confidence:.2f}%")


# ============================================================
# SHAP
# ============================================================

print("\nCalculating SHAP explanation...")

explainer = shap.TreeExplainer(model)

shap_values = explainer.shap_values(flow)

print("SHAP values calculated.")


# ============================================================
# GET SHAP VALUES FOR PREDICTED CLASS
# ============================================================

if isinstance(shap_values, list):

    # Older SHAP format
    values = shap_values[class_index][0]

else:

    # Newer SHAP format
    if shap_values.ndim == 3:

        values = shap_values[0, :, class_index]

    else:

        values = shap_values[0]


# ============================================================
# CREATE FEATURE TABLE
# ============================================================

explanation = pd.DataFrame({
    "Feature": X.columns,
    "SHAP Value": values,
    "Feature Value": flow.iloc[0].values
})

# Sort by absolute SHAP contribution
explanation["Absolute SHAP"] = (
    explanation["SHAP Value"].abs()
)

explanation = explanation.sort_values(
    by="Absolute SHAP",
    ascending=False
)


# ============================================================
# PRINT TOP FEATURES
# ============================================================

print("\nTop features influencing this prediction:")
print("-" * 70)

print(
    explanation.head(10).to_string(index=False)
)


# ============================================================
# PLOT TOP 10
# ============================================================

top_features = explanation.head(10).copy()

top_features = top_features.sort_values(
    by="SHAP Value"
)

plt.figure(figsize=(10, 6))

plt.barh(
    top_features["Feature"],
    top_features["SHAP Value"]
)

plt.axvline(
    0,
    linewidth=1
)

plt.xlabel("SHAP Value")
plt.ylabel("Network Feature")

plt.title(
    f"Why Random Forest Predicted: {prediction}"
)

plt.tight_layout()

plt.savefig(
    RESULT_PATH,
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# DONE
# ============================================================

print("\nExplanation saved:")
print(RESULT_PATH)

print("\n" + "=" * 60)
print("INDIVIDUAL SHAP ANALYSIS COMPLETED")
print("=" * 60)