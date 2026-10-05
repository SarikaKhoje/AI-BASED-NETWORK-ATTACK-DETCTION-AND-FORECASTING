def calculate_risk(
    current_attack_count,
    predicted_attack_count,
    attack_ratio,
    attack_type=None
):
    """
    Calculate network security risk using
    current detection + future forecast.
    """

    score = 0

    # ========================================================
    # 1. CURRENT ATTACK ACTIVITY
    # ========================================================

    if current_attack_count >= 50000:
        score += 40

    elif current_attack_count >= 10000:
        score += 30

    elif current_attack_count >= 1000:
        score += 20

    elif current_attack_count > 0:
        score += 10


    # ========================================================
    # 2. FUTURE ATTACK FORECAST
    # ========================================================

    if predicted_attack_count >= 50000:
        score += 40

    elif predicted_attack_count >= 10000:
        score += 30

    elif predicted_attack_count >= 1000:
        score += 20

    elif predicted_attack_count > 0:
        score += 10


    # ========================================================
    # 3. ATTACK RATIO
    # ========================================================

    if attack_ratio >= 0.50:
        score += 20

    elif attack_ratio >= 0.20:
        score += 15

    elif attack_ratio >= 0.05:
        score += 10

    elif attack_ratio > 0:
        score += 5


    # ========================================================
    # 4. ATTACK TYPE SEVERITY
    # ========================================================

    high_severity_attacks = [
        "DDoS",
        "DoS Hulk",
        "DoS GoldenEye",
        "Heartbleed",
        "Infiltration"
    ]

    if attack_type in high_severity_attacks:
        score += 10


    # ========================================================
    # 5. FINAL RISK LEVEL
    # ========================================================

    if score >= 70:

        risk_level = "CRITICAL"

    elif score >= 50:

        risk_level = "HIGH"

    elif score >= 30:

        risk_level = "MEDIUM"

    else:

        risk_level = "LOW"


    return {
        "risk_score": score,
        "risk_level": risk_level
    }