import pandas as pd
import numpy as np
import json


def preprocess_detection_data(file_path):

    # Load CSV
    data = pd.read_csv(file_path)

    print("Original shape:", data.shape)

    # Columns not used by the model
    remove_columns = [
        "Src IP dec",
        "Dst IP dec",
        "Timestamp",
        "parsed_datetime",
        "Attempted Category"
    ]

    # Remove columns if they exist
    data = data.drop(
        columns=[col for col in remove_columns if col in data.columns]
    )

    # Replace infinity values
    data = data.replace([np.inf, -np.inf], np.nan)

    # Convert values to numeric
    data = data.apply(pd.to_numeric, errors="coerce")

    # Load the 84 features used during training
    with open("models/detection_features.json", "r") as f:
        feature_names = json.load(f)

    # Add missing features
    for feature in feature_names:
        if feature not in data.columns:
            data[feature] = 0

    # Keep exactly the same 84 features
    data = data[feature_names]

    # Replace missing values
    data = data.fillna(0)

    print("After preprocessing:", data.shape)

    return data