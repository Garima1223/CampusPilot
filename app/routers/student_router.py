import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database.db import get_db, SessionLocal
from app.models.models import User, Assignment, Grievance, LibraryBook, LibraryRequest, Course, AttendanceRecord, AttendanceSession
from app.schemas.student_schema import GrievanceCreate, BookRequestCreate
from app.auth.auth import require_role
from app.common import log_audit, notify, parse_pk, build_timetable

router = APIRouter(prefix="/student", tags=["student"])
student_only = require_role(["student"])


def _me(db, current_user):
    u = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not u:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return u


@router.get("/summary")
def summary(db: Session = Depends(get_db), current_user: dict = Depends(student_only)):
    me = _me(db, current_user)
    recs = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == me.id).all()
    pct = round(sum(1 for r in recs if r.present) / len(recs) * 100) if recs else 78
    total_lectures = max(len(recs), 42)
    return {"attendancePct": pct, "cgpa": 8.74, "feeDue": 0,
            "totalLectures": total_lectures, "present": round((pct / 100) * total_lectures)}


@router.get("/assignments")
def assignments(db: Session = Depends(get_db), current_user: dict = Depends(student_only)):
    return [a.to_dict() for a in db.query(Assignment).all()]


@router.post("/assignments/{assignment_id}/submit")
def submit_assignment(assignment_id: str, db: Session = Depends(get_db), current_user: dict = Depends(student_only)):
    me = _me(db, current_user)
    a = db.query(Assignment).filter(Assignment.id == parse_pk(assignment_id)).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    a.status = "submitted"
    db.commit()
    log_audit(db, actor=me.name, actor_role="student", action="Assignment submitted", detail=a.title)
    return a.to_dict()


@router.post("/grievances")
def raise_grievance(payload: GrievanceCreate, db: Session = Depends(get_db), current_user: dict = Depends(student_only)):
    me = _me(db, current_user)
    g = Grievance(raised_by=me.name, role="student", category=payload.category, description=payload.description, status="open")
    db.add(g)
    db.commit()
    db.refresh(g)
    log_audit(db, actor=me.name, actor_role="student", action="Grievance raised",
              detail=f"{g.category} — {g.description[:60]}{'…' if len(g.description) > 60 else ''}")
    notify(db, to_role="admin", title="New grievance submitted", body=f"{me.name} raised a {g.category.lower()} grievance.")
    return g.to_dict()


@router.get("/grievances/mine")
def my_grievances(db: Session = Depends(get_db), current_user: dict = Depends(student_only)):
    me = _me(db, current_user)
    gs = db.query(Grievance).filter(Grievance.raised_by == me.name).all()
    return [g.to_dict() for g in gs]


# ------------------------------------------------------------------- Library
@router.get("/library/catalog")
def library_catalog(db: Session = Depends(get_db), current_user: dict = Depends(student_only)):
    return [b.to_dict() for b in db.query(LibraryBook).all()]


@router.get("/library/requests/mine")
def my_library_requests(db: Session = Depends(get_db), current_user: dict = Depends(student_only)):
    me = _me(db, current_user)
    reqs = db.query(LibraryRequest).filter(LibraryRequest.student_name == me.name).all()
    return [r.to_dict() for r in reqs]


def _resolve_library_request(request_id: int, ready: bool):
    """Runs in the background a few seconds after the request is created,
    mirroring the frontend mock's setTimeout-based 'library desk processes
    your request' simulation — but as a real server-side background task
    with its own DB session, since the request-scoped session is closed by
    the time this fires."""
    db = SessionLocal()
    try:
        req = db.query(LibraryRequest).filter(LibraryRequest.id == request_id).first()
        if not req:
            return
        req.status = "ready-for-pickup" if ready else "waitlisted"
        db.commit()
        body = (f"{req.title} — collect it from the circulation desk." if ready
                else f"{req.title} — all copies are currently out.")
        notify(db, to_role="student", title="Book ready for pickup" if ready else "Added to waitlist", body=body)
    finally:
        db.close()


async def _delayed_resolve(request_id: int, ready: bool):
    await asyncio.sleep(4)
    _resolve_library_request(request_id, ready)


@router.post("/library/requests")
def request_book(payload: BookRequestCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: dict = Depends(student_only)):
    me = _me(db, current_user)
    book = db.query(LibraryBook).filter(LibraryBook.id == parse_pk(payload.book_id)).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    req = LibraryRequest(student_name=me.name, book_id=payload.book_id, title=book.title, status="pending")
    db.add(req)
    db.commit()
    db.refresh(req)
    log_audit(db, actor=me.name, actor_role="student", action="Library request", detail=book.title)
    background_tasks.add_task(_delayed_resolve, req.id, book.copies > 0)
    return req.to_dict()


# ---------------------------------------------------------------- Timetable
@router.get("/timetable")
def timetable(db: Session = Depends(get_db), current_user: dict = Depends(student_only)):
    # No per-student enrollment model in this backend (same as the frontend
    # mock's comment: "mirrors the faculty view") — derives from every course.
    courses = [c.to_dict() for c in db.query(Course).all()]
    return build_timetable(courses)
