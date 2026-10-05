import os
import json
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay
)

import matplotlib.pyplot as plt


# ============================================================
# PATHS
# ============================================================

DATA_PATH = "data/detection_prepared.csv"
MODEL_DIR = "models"
RESULT_DIR = "results"

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 60)
print("RANDOM FOREST - NETWORK ATTACK DETECTION")
print("=" * 60)

df = pd.read_csv(DATA_PATH)

print("\nDataset loaded successfully.")
print("Rows:", len(df))
print("Columns:", len(df.columns))


# ============================================================
# BASIC VALIDATION
# ============================================================

print("\n--- DATA VALIDATION ---")

print("Missing values:", df.isnull().sum().sum())

print(
    "Infinite values:",
    df.select_dtypes(include="number")
      .isin([float("inf"), float("-inf")])
      .sum()
      .sum()
)

print("Duplicate rows:", df.duplicated().sum())

print("Number of classes:", df["Label"].nunique())

print("\nClasses:")
print(df["Label"].unique())


# ============================================================
# SEPARATE FEATURES AND TARGET
# ============================================================

X = df.drop(columns=["Label"])
y = df["Label"]

# Make sure all features are numeric
X = X.select_dtypes(include=["number"])

print("\nNumber of model features:", X.shape[1])


# ============================================================
# SAVE FEATURE ORDER
# ============================================================

feature_names = X.columns.tolist()

with open(
    os.path.join(MODEL_DIR, "detection_features.json"),
    "w"
) as f:
    json.dump(feature_names, f, indent=4)

print("\nFeature order saved.")


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\n--- DATA SPLIT ---")
print("Training rows:", len(X_train))
print("Testing rows:", len(X_test))


# ============================================================
# RANDOM FOREST
# ============================================================

print("\n--- TRAINING RANDOM FOREST ---")

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
    n_jobs=-1,
    class_weight="balanced"
)

model.fit(X_train, y_train)

print("Training completed.")


# ============================================================
# PREDICTION
# ============================================================

y_pred = model.predict(X_test)


# ============================================================
# EVALUATION
# ============================================================

accuracy = accuracy_score(y_test, y_pred)

precision = precision_score(
    y_test,
    y_pred,
    average="weighted",
    zero_division=0
)

recall = recall_score(
    y_test,
    y_pred,
    average="weighted",
    zero_division=0
)

f1 = f1_score(
    y_test,
    y_pred,
    average="weighted",
    zero_division=0
)

print("\n" + "=" * 60)
print("MODEL PERFORMANCE")
print("=" * 60)

print(f"Accuracy : {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall   : {recall:.4f}")
print(f"F1 Score : {f1:.4f}")


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

print("\n--- CLASSIFICATION REPORT ---")

print(
    classification_report(
        y_test,
        y_pred,
        zero_division=0
    )
)


# ============================================================
# CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(y_test, y_pred)

disp = ConfusionMatrixDisplay(
    confusion_matrix=cm,
    display_labels=model.classes_
)

fig, ax = plt.subplots(figsize=(14, 12))

disp.plot(
    ax=ax,
    xticks_rotation=90,
    cmap="Blues",
    colorbar=False
)

plt.title("Random Forest - Network Attack Detection")
plt.tight_layout()

confusion_path = os.path.join(
    RESULT_DIR,
    "confusion_matrix.png"
)

plt.savefig(confusion_path, dpi=300)
plt.close()

print("\nConfusion matrix saved:")
print(confusion_path)


# ============================================================
# SAVE MODEL
# ============================================================

model_path = os.path.join(
    MODEL_DIR,
    "detection_model.pkl"
)

joblib.dump(model, model_path)

print("\nModel saved:")
print(model_path)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 60)
print("DETECTION MODEL TRAINING COMPLETED")
print("=" * 60)