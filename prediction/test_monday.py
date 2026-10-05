import joblib
import pandas as pd

from preprocessing.detection_preprocessor import preprocess_detection_data


MODEL_PATH = "models/detection_model.pkl"
DATA_PATH = "data/wednesday.csv"


# Preprocess Monday data
X = preprocess_detection_data(DATA_PATH)

# Load trained model
model = joblib.load(MODEL_PATH)

# Predict all flows
predictions = model.predict(X)


# Convert predictions into a Series
prediction_counts = pd.Series(predictions).value_counts()


# Total flows
total_flows = len(predictions)

# BENIGN flows
benign_flows = prediction_counts.get("BENIGN", 0)

# Attack flows
attack_flows = total_flows - benign_flows


print("=" * 60)
print("MONDAY.CSV FULL DATA TEST")
print("=" * 60)

print("Total flows:", total_flows)

print("BENIGN flows:", benign_flows)

print("Predicted attack flows:", attack_flows)

print("\nPrediction percentage:")

for attack_type, count in prediction_counts.items():

    percentage = (count / total_flows) * 100

    print(
        f"{attack_type}: "
        f"{count} flows "
        f"({percentage:.2f}%)"
    )