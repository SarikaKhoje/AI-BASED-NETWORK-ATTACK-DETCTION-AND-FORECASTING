import joblib
import json

from preprocessing.detection_preprocessor import preprocess_detection_data


MODEL_PATH = "models/detection_model.pkl"
FEATURE_PATH = "models/detection_features.json"
DATA_PATH = "data/monday.csv"


# Preprocess new data
X = preprocess_detection_data(DATA_PATH)


# Load trained model
model = joblib.load(MODEL_PATH)


# Predict
predictions = model.predict(X)
probabilities = model.predict_proba(X)


print("=" * 60)
print("NEW DATA MODEL TEST - MONDAY.CSV")
print("=" * 60)

# Show only first 10 flows
for i in range(min(10, len(predictions))):

    confidence = probabilities[i].max() * 100

    print(
        f"Flow {i + 1}: "
        f"Prediction = {predictions[i]} | "
        f"Confidence = {confidence:.2f}%"
    )