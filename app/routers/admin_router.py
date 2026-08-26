from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import (
    User, Course, SubjectRequest, Fee, Grievance, AuditLogEntry,
    AttendanceRecord, GradeEntry,
)
from app.schemas.user_schema import UserCreateByAdmin, UserStatusUpdate
from app.schemas.admin_schema import CourseCreate, SubjectRejectRequest, GrievanceAssignRequest
from app.auth.auth import require_role, hash_password
from app.common import log_audit, notify, parse_pk, compute_risk_score, fee_status_for_student_name

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require_role(["admin"])


# ---------------------------------------------------------------------- Users
@router.get("/users")
def list_users(db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    return [u.to_dict() for u in db.query(User).all()]


@router.post("/users")
def create_user(payload: UserCreateByAdmin, db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    if db.query(User).filter(User.email.ilike(payload.email.strip().lower())).first():
        raise HTTPException(status_code=400, detail="An account with that email already exists.")
    user = User(
        name=payload.name, email=payload.email, role=payload.role, id_label=payload.id_label,
        department=payload.department, designation=payload.designation, phone=payload.phone,
        status="active", password_hash=hash_password("changeme123"),  # matches frontend's default demo password
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_audit(db, actor=current_user["name"], actor_role="admin", action="User created", detail=f"{user.name} ({user.role})")
    return user.to_dict()


@router.patch("/users/{user_id}/status")
def set_user_status(user_id: str, payload: UserStatusUpdate, db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    u = db.query(User).filter(User.id == parse_pk(user_id)).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.status = payload.status
    db.commit()
    log_audit(db, actor=current_user["name"], actor_role="admin",
              action="User reactivated" if payload.status == "active" else "User deactivated", detail=u.name)
    return u.to_dict()


# -------------------------------------------------------------------- Courses
@router.get("/courses")
def list_courses(db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    return [c.to_dict() for c in db.query(Course).all()]


@router.post("/courses")
def create_course(payload: CourseCreate, db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    course = Course(code=payload.code, name=payload.name, dept=payload.dept, faculty=payload.faculty, students=0)
    db.add(course)
    db.commit()
    db.refresh(course)
    log_audit(db, actor=current_user["name"], actor_role="admin", action="Course created", detail=f"{course.code} — {course.name}")
    return course.to_dict()


# ------------------------------------------------------- Subject requests
@router.get("/subject-requests")
def list_subject_requests(db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    reqs = db.query(SubjectRequest).order_by(SubjectRequest.ts.desc()).all()
    return [r.to_dict() for r in reqs]


@router.post("/subject-requests/{req_id}/approve")
def approve_subject_request(req_id: str, db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    req = db.query(SubjectRequest).filter(SubjectRequest.id == parse_pk(req_id)).first()
    if not req:
        raise HTTPException(status_code=404, detail="Subject request not found")
    req.status = "approved"
    course = Course(code=req.code, name=req.name, dept=req.dept, faculty=req.teacher_name, students=0)
    db.add(course)
    db.commit()
    log_audit(db, actor=current_user["name"], actor_role="admin", action="Subject request approved",
              detail=f"{req.code} — {req.name} → {req.teacher_name}")
    notify(db, to_role="teacher", title="Subject request approved", body=f"{req.code} — {req.name} was added to your subjects.")
    return req.to_dict()


@router.post("/subject-requests/{req_id}/reject")
def reject_subject_request(req_id: str, payload: SubjectRejectRequest, db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    req = db.query(SubjectRequest).filter(SubjectRequest.id == parse_pk(req_id)).first()
    if not req:
        raise HTTPException(status_code=404, detail="Subject request not found")
    req.status = "rejected"
    req.reject_reason = payload.reason or ""
    db.commit()
    log_audit(db, actor=current_user["name"], actor_role="admin", action="Subject request rejected", detail=f"{req.code} — {req.name}")
    body = f"{req.code} — {req.name}: {payload.reason}" if payload.reason else f"{req.code} — {req.name} was not approved."
    notify(db, to_role="teacher", title="Subject request declined", body=body)
    return req.to_dict()


# ----------------------------------------------------------------------- Fees
@router.get("/fees")
def list_fees(db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    return [f.to_dict() for f in db.query(Fee).all()]


@router.post("/fees/{fee_id}/mark-paid")
def mark_fee_paid(fee_id: str, db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    f = db.query(Fee).filter(Fee.id == parse_pk(fee_id)).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fee record not found")
    f.paid = f.total
    f.status = "paid"
    db.commit()
    log_audit(db, actor=current_user["name"], actor_role="admin", action="Fee marked paid", detail=f.student)
    return f.to_dict()


# ------------------------------------------------------------------- Reports
@router.get("/reports/summary")
def reports_summary(db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    total_students = db.query(User).filter(User.role == "student").count()
    total_teachers = db.query(User).filter(User.role == "teacher").count()
    total_courses = db.query(Course).count()
    fees = db.query(Fee).all()
    billed = sum(f.total for f in fees)
    collected = sum(f.paid for f in fees)
    return {
        "totalStudents": total_students,
        "totalTeachers": total_teachers,
        "totalCourses": total_courses,
        "feeCollectedPct": round((collected / billed) * 100) if billed else 0,
        "avgAttendance": 78,
        "avgCGPA": 8.1,
        "attendanceByDept": [
            {"label": "CS", "value": 82}, {"label": "Math", "value": 76},
            {"label": "EE", "value": 71}, {"label": "ME", "value": 69},
        ],
    }


@router.get("/audit-log")
def audit_log(db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    entries = db.query(AuditLogEntry).order_by(AuditLogEntry.ts.desc()).limit(60).all()
    return [e.to_dict() for e in entries]


# --------------------------------------------------------------- Grievances
@router.get("/grievances")
def list_grievances(db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    gs = db.query(Grievance).order_by(Grievance.ts.desc()).all()
    return [g.to_dict() for g in gs]


@router.post("/grievances/{grv_id}/assign")
def assign_grievance(grv_id: str, payload: GrievanceAssignRequest, db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    g = db.query(Grievance).filter(Grievance.id == parse_pk(grv_id)).first()
    if not g:
        raise HTTPException(status_code=404, detail="Grievance not found")
    g.assigned_to = payload.assignee
    if g.status == "open":
        g.status = "in-review"
    db.commit()
    log_audit(db, actor=current_user["name"], actor_role="admin", action="Grievance assigned", detail=f"{g.category} → {payload.assignee}")
    return g.to_dict()


@router.post("/grievances/{grv_id}/resolve")
def resolve_grievance(grv_id: str, db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    g = db.query(Grievance).filter(Grievance.id == parse_pk(grv_id)).first()
    if not g:
        raise HTTPException(status_code=404, detail="Grievance not found")
    g.status = "resolved"
    db.commit()
    log_audit(db, actor=current_user["name"], actor_role="admin", action="Grievance resolved", detail=g.category)
    notify(db, to_role=g.role, title="Grievance resolved", body=f"Your {g.category.lower()} grievance has been resolved.")
    return g.to_dict()


# ------------------------------------------------------------- Risk scores
@router.get("/risk-scores")
def risk_scores(db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    """Campus-wide risk scoring — same heuristic teachers see, applied to every student on record."""
    students = db.query(User).filter(User.role == "student").all()
    out = []
    for s in students:
        recs = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == s.id).all()
        attendance_pct = round(sum(1 for r in recs if r.present) / len(recs) * 100) if recs else 82
        entries = db.query(GradeEntry).filter(GradeEntry.student_id == s.id).all()
        avg_score = round(sum(e.score for e in entries) / len(entries)) if entries else 75
        fee_status = fee_status_for_student_name(db, s.name)
        risk = compute_risk_score(attendance_pct, avg_score, fee_status)
        out.append({"id": f"u_{s.id}", "name": s.name, "idLabel": s.id_label,
                     "attendancePct": attendance_pct, "avgScore": avg_score, "feeStatus": fee_status, **risk})
    return out
