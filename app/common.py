"""
Small shared helpers used across routers — ports the frontend's
pushAudit()/pushNotification() (App.jsx) to the server side so every router
logs the same way instead of repeating this in each file.
"""
from app.models.models import AuditLogEntry, Notification, User, Fee

# ---------------------------------------------------------------------------
# Risk-insights heuristic — ported 1:1 from computeRiskScore() in App.jsx so
# admin and teacher views produce the same numbers the frontend already
# documents to users as "a demo heuristic, not a trained ML model".
#   healthScore = 0.45*attendancePct + 0.35*avgScore + 0.20*feeComponent
#   feeComponent: paid=100, partial=50, overdue=0, unknown=75
#   riskLevel: >=75 low, >=50 medium, else high
# ---------------------------------------------------------------------------
RISK_WEIGHTS = {"attendance": 0.45, "score": 0.35, "fee": 0.20}
RISK_THRESHOLDS = {"low": 75, "medium": 50}


def fee_component_for(fee_status):
    if fee_status == "paid":
        return 100
    if fee_status == "partial":
        return 50
    if fee_status == "overdue":
        return 0
    return 75


def compute_risk_score(attendance_pct: float, avg_score: float, fee_status):
    fee_component = fee_component_for(fee_status)
    health_score = round(
        RISK_WEIGHTS["attendance"] * attendance_pct +
        RISK_WEIGHTS["score"] * avg_score +
        RISK_WEIGHTS["fee"] * fee_component
    )
    risk_level = "low" if health_score >= RISK_THRESHOLDS["low"] else (
        "medium" if health_score >= RISK_THRESHOLDS["medium"] else "high")

    reasons = []
    if attendance_pct < 75:
        reasons.append(f"Attendance {round(attendance_pct)}% (below 75%)")
    if avg_score < 50:
        reasons.append(f"Avg. score {round(avg_score)}/100 (below 50)")
    if fee_status == "overdue":
        reasons.append("Fee overdue")
    elif fee_status == "partial":
        reasons.append("Fee partially paid")
    if not reasons:
        reasons.append("No risk factors flagged")

    return {"healthScore": health_score, "riskLevel": risk_level, "reasons": reasons, "feeComponent": fee_component}


def fee_status_for_student_name(db, name: str):
    fee = db.query(Fee).filter(Fee.student == name).first()
    return fee.status if fee else "unknown"


# ---------------------------------------------------------------------------
# Timetable — ported 1:1 from buildTimetable() in App.jsx: a deterministic
# weekly grid derived from a course list, no separate enrollment/timetable
# table needed (matches the frontend's "derived, not stored" comment).
# ---------------------------------------------------------------------------
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
DAY_SLOTS = ["9:00 AM", "10:00 AM", "11:15 AM", "12:30 PM", "2:00 PM", "3:15 PM"]
ROOMS = ["B-204", "Lab 3", "A-102", "B-118", "C-210", "Lab 1"]


def build_timetable(courses):
    """courses: list of dicts with at least name/code (a Course.to_dict() list works directly)."""
    grid = {d: [] for d in WEEKDAYS}
    if not courses:
        return grid
    slot_cursor = 0
    for ci, course in enumerate(courses):
        sessions_per_week = 3
        for s in range(sessions_per_week):
            day_idx = (ci * 2 + s * 2 + 1) % len(WEEKDAYS)
            day = WEEKDAYS[day_idx]
            slot = DAY_SLOTS[slot_cursor % len(DAY_SLOTS)]
            grid[day].append({"time": slot, "course": course["name"], "code": course["code"], "room": ROOMS[(ci + s) % len(ROOMS)]})
            slot_cursor += 1
    for d in WEEKDAYS:
        grid[d].sort(key=lambda a: DAY_SLOTS.index(a["time"]))
    return grid


def grade_distribution(scores):
    """Buckets a list of numeric scores into A/B/C/D/F bands for a distribution chart."""
    bands = [("A", 85), ("B", 70), ("C", 55), ("D", 40), ("F", 0)]
    counts = [{"label": label, "value": 0} for label, _ in bands]
    for score in scores:
        for idx, (label, minimum) in enumerate(bands):
            if score >= minimum:
                counts[idx]["value"] += 1
                break
    return counts


def log_audit(db, actor: str, actor_role: str, action: str, detail: str = ""):
    entry = AuditLogEntry(actor=actor, actor_role=actor_role, action=action, detail=detail)
    db.add(entry)
    db.commit()
    return entry


def notify(db, to_role: str, title: str, body: str):
    n = Notification(to_role=to_role, title=title, body=body)
    db.add(n)
    db.commit()
    return n


def parse_pk(prefixed_id: str) -> int:
    """'u_5' -> 5, 'c_12' -> 12, etc. Raises ValueError on a malformed id."""
    return int(str(prefixed_id).rsplit("_", 1)[-1])


def get_user_or_404(db, current_user_id: int):
    from fastapi import HTTPException
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
