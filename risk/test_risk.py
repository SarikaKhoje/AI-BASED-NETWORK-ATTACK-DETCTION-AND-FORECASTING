from risk.risk_engine import calculate_risk


# Current detection
current_attack_count = 61883

# Forecast from Gradient Boosting
predicted_attack_count = 44260

# Current attack ratio
attack_ratio = 0.35

# Attack detected by Random Forest
attack_type = "DoS Hulk"


result = calculate_risk(
    current_attack_count,
    predicted_attack_count,
    attack_ratio,
    attack_type
)


print("=" * 60)
print("NETWORK SECURITY RISK")
print("=" * 60)

print(
    "Current attack count:",
    current_attack_count
)

print(
    "Predicted attack count:",
    predicted_attack_count
)

print(
    "Attack ratio:",
    attack_ratio
)

print(
    "Attack type:",
    attack_type
)

print(
    "Risk score:",
    result["risk_score"]
)

print(
    "Risk level:",
    result["risk_level"]
)

print("=" * 60)