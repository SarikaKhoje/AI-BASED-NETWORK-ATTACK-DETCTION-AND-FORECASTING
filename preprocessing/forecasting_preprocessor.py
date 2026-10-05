import pandas as pd
import numpy as np


def prepare_forecast_input(
    file_path,
    date,
    detection_model=None
):

    print("=" * 60)
    print("FORECASTING PREPROCESSING PIPELINE")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. LOAD RAW DATA
    # --------------------------------------------------------

    data = pd.read_csv(file_path)

    print("Raw data shape:", data.shape)

    # --------------------------------------------------------
    # 2. REMOVE DUPLICATES
    # --------------------------------------------------------

    data = data.drop_duplicates().copy()

    # --------------------------------------------------------
    # 3. HANDLE INFINITY
    # --------------------------------------------------------

    data = data.replace(
        [np.inf, -np.inf],
        np.nan
    )

    # --------------------------------------------------------
    # 4. CONVERT NUMERIC COLUMNS
    # --------------------------------------------------------

    non_numeric = [
        "Timestamp",
        "Label",
        "Attempted Category"
    ]

    for column in data.columns:

        if column not in non_numeric:

            data[column] = pd.to_numeric(
                data[column],
                errors="coerce"
            )

    # --------------------------------------------------------
    # 5. CREATE DATETIME
    # --------------------------------------------------------

    time_values = pd.to_timedelta(
        data["Timestamp"].astype(str).str.strip(),
        errors="coerce"
    )

    data["parsed_datetime"] = (
        pd.Timestamp(date)
        + time_values
    )

    data = data.dropna(
        subset=["parsed_datetime"]
    ).copy()

    # --------------------------------------------------------
    # 6. HANDLE MISSING NUMERIC VALUES
    # --------------------------------------------------------

    numeric_columns = data.select_dtypes(
        include=["number"]
    ).columns

    data[numeric_columns] = (
        data[numeric_columns].fillna(0)
    )

    # --------------------------------------------------------
    # 7. SORT BY TIME
    # --------------------------------------------------------

    data = (
        data
        .sort_values("parsed_datetime")
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # 8. DETERMINE ATTACK FLOWS
    # --------------------------------------------------------

    if detection_model is None:

        # Historical/demo data
        # Use actual Label

        data["is_attack"] = (
            data["Label"]
            .astype(str)
            .str.strip()
            != "BENIGN"
        )

    else:

        # Live/prediction data
        # Use Random Forest prediction

        detection_features = [
            "Src Port",
            "Dst Port",
            "Protocol",
            "Flow Duration",
            "Total Fwd Packet",
            "Total Bwd packets",
            "Total Length of Fwd Packet",
            "Total Length of Bwd Packet",
            "Fwd Packet Length Max",
            "Fwd Packet Length Min",
            "Fwd Packet Length Mean",
            "Fwd Packet Length Std",
            "Bwd Packet Length Max",
            "Bwd Packet Length Min",
            "Bwd Packet Length Mean",
            "Bwd Packet Length Std",
            "Flow Bytes/s",
            "Flow Packets/s",
            "Flow IAT Mean",
            "Flow IAT Std",
            "Flow IAT Max",
            "Flow IAT Min",
            "Fwd IAT Total",
            "Fwd IAT Mean",
            "Fwd IAT Std",
            "Fwd IAT Max",
            "Fwd IAT Min",
            "Bwd IAT Total",
            "Bwd IAT Mean",
            "Bwd IAT Std",
            "Bwd IAT Max",
            "Bwd IAT Min",
            "Fwd PSH Flags",
            "Bwd PSH Flags",
            "Fwd URG Flags",
            "Bwd URG Flags",
            "Fwd RST Flags",
            "Bwd RST Flags",
            "Fwd Header Length",
            "Bwd Header Length",
            "Fwd Packets/s",
            "Bwd Packets/s",
            "Packet Length Min",
            "Packet Length Max",
            "Packet Length Mean",
            "Packet Length Std",
            "Packet Length Variance",
            "FIN Flag Count",
            "SYN Flag Count",
            "RST Flag Count",
            "PSH Flag Count",
            "ACK Flag Count",
            "URG Flag Count",
            "CWR Flag Count",
            "ECE Flag Count",
            "Down/Up Ratio",
            "Average Packet Size",
            "Fwd Segment Size Avg",
            "Bwd Segment Size Avg",
            "Fwd Bytes/Bulk Avg",
            "Fwd Packet/Bulk Avg",
            "Fwd Bulk Rate Avg",
            "Bwd Bytes/Bulk Avg",
            "Bwd Packet/Bulk Avg",
            "Bwd Bulk Rate Avg",
            "Subflow Fwd Packets",
            "Subflow Fwd Bytes",
            "Subflow Bwd Packets",
            "Subflow Bwd Bytes",
            "FWD Init Win Bytes",
            "Bwd Init Win Bytes",
            "Fwd Act Data Pkts",
            "Fwd Seg Size Min",
            "Active Mean",
            "Active Std",
            "Active Max",
            "Active Min",
            "Idle Mean",
            "Idle Std",
            "Idle Max",
            "Idle Min",
            "ICMP Code",
            "ICMP Type",
            "Total TCP Flow Time"
        ]

        X_detection = data[
            detection_features
        ]

        predictions = detection_model.predict(
            X_detection
        )

        data["is_attack"] = (
            predictions != "BENIGN"
        )

    # --------------------------------------------------------
    # 9. CREATE 5-MINUTE WINDOWS
    # --------------------------------------------------------

    data["time_window"] = (
        data["parsed_datetime"]
        .dt.floor("5min")
    )

    # --------------------------------------------------------
    # 10. AGGREGATE NETWORK TRAFFIC
    # --------------------------------------------------------

    windows = (
        data
        .groupby("time_window")
        .agg(

            total_flows=(
                "parsed_datetime",
                "count"
            ),

            attack_flows=(
                "is_attack",
                "sum"
            ),

            avg_packet_rate=(
                "Flow Packets/s",
                "mean"
            ),

            avg_byte_rate=(
                "Flow Bytes/s",
                "mean"
            ),

            avg_flow_duration=(
                "Flow Duration",
                "mean"
            ),

            syn_count=(
                "SYN Flag Count",
                "sum"
            ),

            rst_count=(
                "RST Flag Count",
                "sum"
            ),

            unique_src_ip=(
                "Src IP dec",
                "nunique"
            ),

            unique_dst_ip=(
                "Dst IP dec",
                "nunique"
            )
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # 11. NORMAL FLOWS
    # --------------------------------------------------------

    windows["normal_flows"] = (
        windows["total_flows"]
        - windows["attack_flows"]
    )

    # --------------------------------------------------------
    # 12. ATTACK RATIO
    # --------------------------------------------------------

    windows["attack_ratio"] = np.where(

        windows["total_flows"] > 0,

        windows["attack_flows"]
        / windows["total_flows"],

        0
    )

    # --------------------------------------------------------
    # 13. LAG FEATURES
    # --------------------------------------------------------

    windows["attack_count_lag_1"] = (
        windows["attack_flows"].shift(1)
    )

    windows["attack_count_lag_2"] = (
        windows["attack_flows"].shift(2)
    )

    windows["attack_count_lag_3"] = (
        windows["attack_flows"].shift(3)
    )

    # --------------------------------------------------------
    # 14. ROLLING FEATURES
    # --------------------------------------------------------

    previous_attack = (
        windows["attack_flows"].shift(1)
    )

    windows["rolling_mean_3"] = (
        previous_attack
        .rolling(3)
        .mean()
    )

    windows["rolling_std_3"] = (
        previous_attack
        .rolling(3)
        .std()
    )

    windows["rolling_max_3"] = (
        previous_attack
        .rolling(3)
        .max()
    )

    # --------------------------------------------------------
    # 15. REMOVE INVALID FIRST WINDOWS
    # --------------------------------------------------------

    required = [
        "attack_count_lag_1",
        "attack_count_lag_2",
        "attack_count_lag_3",
        "rolling_mean_3",
        "rolling_std_3",
        "rolling_max_3"
    ]

    windows = windows.dropna(
        subset=required
    )

    # --------------------------------------------------------
    # 16. RENAME TIMESTAMP
    # --------------------------------------------------------

    windows = windows.rename(
        columns={
            "time_window": "parsed_datetime"
        }
    )

    # --------------------------------------------------------
    # 17. FINAL MODEL FEATURES
    # --------------------------------------------------------

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

    windows = (
        windows[
            ["parsed_datetime"] + features
        ]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .dropna()
        .reset_index(drop=True)
    )

    print()
    print("Forecasting windows:", len(windows))
    print("Features:", len(features))

    print()
    print("Latest window:")
    print(
        windows[
            ["parsed_datetime", "attack_flows"]
        ].tail(1)
    )

    print()
    print("=" * 60)
    print("PREPROCESSING COMPLETED")
    print("=" * 60)

    return windows