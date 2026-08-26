from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import User, AttendanceRecord, GradeEntry, Placement, PlacementApplication, Grievance
from app.schemas.copilot_schema import CopilotQuestion
from app.auth.auth import require_role
from app.common import compute_risk_score, fee_status_for_student_name
from app.ai.copilot import detect_intent, extract_subject

router = APIRouter(prefix="/copilot", tags=["copilot"])
student_only = require_role(["student"])


@router.post("/ask")
def ask_copilot(data: CopilotQuestion, db: Session = Depends(get_db), current_user: dict = Depends(student_only)):
    """
    The frontend's floating Copilot widget currently answers from a
    canned/local rule set and explicitly documents itself as swappable for
    "a real LLM call (e.g. POST /api/v1/copilot/ask)" — this is that
    endpoint, backed by the same real data the rest of the app now persists
    (attendance records, grades, placements, grievances) instead of mock
    fixture arrays.
    """
    student = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not student:
        raise HTTPException(status_code=400, detail="No student profile linked to this account")

    intent = detect_intent(data.question)

    if intent == "attendance":
        recs = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.id).all()
        if not recs:
            return {"answer": "I couldn't find any attendance records for you yet."}
        present = sum(1 for r in recs if r.present)
        percent = round(present / len(recs) * 100, 1)
        return {"answer": f"Your attendance is {percent}%, based on {present} present out of {len(recs)} recorded classes."}

    if intent == "risk":
        entries = db.query(GradeEntry).filter(GradeEntry.student_id == student.id).all()
        avg_score = round(sum(e.score for e in entries) / len(entries)) if entries else 75
        recs = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student.id).all()
        attendance_pct = round(sum(1 for r in recs if r.present) / len(recs) * 100) if recs else 82
        fee_status = fee_status_for_student_name(db, student.name)
        risk = compute_risk_score(attendance_pct, avg_score, fee_status)
        return {"answer": f"Your current risk level is {risk['riskLevel']} (score: {risk['healthScore']}). "
                           f"{'; '.join(risk['reasons'])}."}

    if intent == "placement":
        applied_ids = {a.placement_id for a in db.query(PlacementApplication).filter(PlacementApplication.student_id == f"u_{student.id}").all()}
        open_postings = db.query(Placement).filter(Placement.status == "open").all()
        eligible = [p for p in open_postings if f"pl_{p.id}" not in applied_ids]
        if not eligible:
            return {"answer": "There are no open placement postings you haven't already applied to."}
        listing = "; ".join(f"{p.role} at {p.company}" for p in eligible[:5])
        return {"answer": f"You're eligible to apply for: {listing}"}

    if intent == "grievance":
        grievances = db.query(Grievance).filter(Grievance.raised_by == student.name).all()
        if not grievances:
            return {"answer": "You haven't submitted any grievances yet."}
        open_count = sum(1 for g in grievances if g.status == "open")
        return {"answer": f"You have {len(grievances)} grievance(s) submitted, {open_count} currently open."}

    return {"answer": "I can help with questions about your attendance, risk status, job eligibility, or grievances. Try asking about one of those."}
