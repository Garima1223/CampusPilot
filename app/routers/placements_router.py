from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import User, Placement, PlacementApplication
from app.schemas.placement_schema import PlacementCreate, ApplicationStatusUpdate
from app.auth.auth import get_current_user, require_role
from app.common import log_audit, notify, parse_pk

router = APIRouter(prefix="/placements", tags=["placements"])
admin_only = require_role(["admin"])
student_only = require_role(["student"])


@router.get("/")
def list_placements(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return [p.to_dict() for p in db.query(Placement).all()]


@router.post("/")
def create_placement(payload: PlacementCreate, db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    me = db.query(User).filter(User.id == current_user["user_id"]).first()
    p = Placement(company=payload.company, role=payload.role, package=payload.package, location=payload.location,
                   min_cgpa=payload.min_cgpa, min_attendance=payload.min_attendance, deadline=payload.deadline,
                   posted_by=me.name, status="open")
    db.add(p)
    db.commit()
    db.refresh(p)
    log_audit(db, actor=me.name, actor_role="admin", action="Placement posted", detail=f"{p.company} — {p.role}")
    notify(db, to_role="student", title="New placement drive", body=f"{p.company} is hiring for {p.role}.")
    return p.to_dict()


@router.post("/{placement_id}/apply")
def apply(placement_id: str, db: Session = Depends(get_db), current_user: dict = Depends(student_only)):
    me = db.query(User).filter(User.id == current_user["user_id"]).first()
    posting = db.query(Placement).filter(Placement.id == parse_pk(placement_id)).first()
    if not posting:
        raise HTTPException(status_code=404, detail="This posting is no longer available.")
    student_ref = f"u_{me.id}"
    if db.query(PlacementApplication).filter(PlacementApplication.placement_id == placement_id,
                                              PlacementApplication.student_id == student_ref).first():
        raise HTTPException(status_code=400, detail="You've already applied to this posting.")
    app_ = PlacementApplication(placement_id=placement_id, student_id=student_ref, student_name=me.name,
                                 id_label=me.id_label, status="applied")
    db.add(app_)
    db.commit()
    db.refresh(app_)
    log_audit(db, actor=me.name, actor_role="student", action="Placement application submitted",
              detail=f"{me.name} → {posting.company} ({posting.role})")
    notify(db, to_role="admin", title="New placement application", body=f"{me.name} applied to {posting.company}.")
    return app_.to_dict()


@router.get("/mine")
def my_applications(db: Session = Depends(get_db), current_user: dict = Depends(student_only)):
    me = db.query(User).filter(User.id == current_user["user_id"]).first()
    apps = db.query(PlacementApplication).filter(PlacementApplication.student_id == f"u_{me.id}").all()
    return [a.to_dict() for a in apps]


@router.get("/{placement_id}/applicants")
def list_applicants(placement_id: str, db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    apps = db.query(PlacementApplication).filter(PlacementApplication.placement_id == placement_id).all()
    return [a.to_dict() for a in apps]


@router.patch("/applications/{app_id}")
def set_application_status(app_id: str, payload: ApplicationStatusUpdate, db: Session = Depends(get_db), current_user: dict = Depends(admin_only)):
    me = db.query(User).filter(User.id == current_user["user_id"]).first()
    app_ = db.query(PlacementApplication).filter(PlacementApplication.id == parse_pk(app_id)).first()
    if not app_:
        raise HTTPException(status_code=404, detail="Application not found")
    app_.status = payload.status
    db.commit()
    log_audit(db, actor=me.name, actor_role="admin", action="Application status updated", detail=f"{app_.student_name} → {payload.status}")
    notify(db, to_role="student", title="Placement update", body=f'Your application status changed to "{payload.status}".')
    return app_.to_dict()
