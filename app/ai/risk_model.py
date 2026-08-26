def calculate_risk(attendance_percent: float, internal_marks: float, backlogs: int):
    """
    Simple rule-based risk scoring (MVP version before training a real ML model).
    Returns a risk score (0-100), level, reason, and recommendation.
    """
    score = 0
    reasons = []

    if attendance_percent < 75:
        score += 35
        reasons.append(f"Attendance below 75% ({attendance_percent}%)")

    if internal_marks < 50:
        score += 30
        reasons.append(f"Low internal marks ({internal_marks})")

    if backlogs > 0:
        score += 20 * backlogs
        reasons.append(f"{backlogs} backlog(s)")

    score = min(score, 100)

    if score >= 60:
        level = "HIGH"
        recommendation = "Schedule immediate faculty intervention and parent notification."
    elif score >= 30:
        level = "MEDIUM"
        recommendation = "Monitor closely and schedule a faculty check-in."
    else:
        level = "LOW"
        recommendation = "No action needed. Continue regular monitoring."

    reason_text = "; ".join(reasons) if reasons else "No significant risk factors."

    return {
        "risk_score": score,
        "risk_level": level,
        "reason": reason_text,
        "recommendation": recommendation
    }