from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import Notification
from app.auth.auth import get_current_user
from app.common import parse_pk

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/")
def my_notifications(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    The frontend mock broadcasts notifications by role (toRole: 'student' |
    'teacher' | 'admin') rather than to a specific user id, and the current
    UI consumes them live off an in-memory event bus rather than polling a
    REST endpoint. This endpoint exists for parity with a real backend need
    (there's no event bus across an HTTP boundary) — it returns everything
    broadcast to the caller's role, newest first.
    """
    notes = (
        db.query(Notification)
        .filter(Notification.to_role == current_user["role"])
        .order_by(Notification.ts.desc())
        .limit(100)
        .all()
    )
    return [n.to_dict() for n in notes]


@router.patch("/{notification_id}/read")
def mark_as_read(notification_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == parse_pk(notification_id), Notification.to_role == current_user["role"]).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.read = True
    db.commit()
    return {"message": "Marked as read"}
