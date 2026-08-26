from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.db import Base

# ---------------------------------------------------------------------------
# NOTE ON SHAPE: these models intentionally mirror the flat shape of the
# CampusPilot React frontend's mock `DB` object (App.jsx) rather than a
# from-scratch normalized schema, so the JSON each endpoint returns can match
# what the frontend already expects field-for-field. Every model exposes a
# to_dict() that produces exactly that shape (camelCase keys where the
# frontend uses them) instead of relying on FastAPI's default serialization
# of SQLAlchemy objects, so the mapping from DB column -> frontend field is
# explicit and in one place per model.
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150))
    email = Column(String(150), unique=True, index=True)
    password_hash = Column(String(255))
    role = Column(String(20))  # "student" | "teacher" | "admin" — matches the frontend's ROLES keys
    id_label = Column(String(50))  # roll number / staff ID / admin ID, display-only
    status = Column(String(20), default="active")  # "active" | "inactive"

    # Faculty-profile-only fields (nullable for student/admin accounts) —
    # kept on the same row rather than a separate Teacher table because the
    # frontend's DB.users is a single flat list with these fields present
    # only on teacher records.
    phone = Column(String(30), nullable=True)
    department = Column(String(120), nullable=True)
    designation = Column(String(120), nullable=True)
    qualification = Column(String(255), nullable=True)
    joined = Column(String(50), nullable=True)
    office = Column(String(120), nullable=True)
    bio = Column(Text, nullable=True)

    def to_dict(self, include_private=False):
        d = {
            "id": f"u_{self.id}",
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "idLabel": self.id_label,
            "status": self.status,
        }
        if self.role == "teacher":
            d.update({
                "phone": self.phone,
                "department": self.department,
                "designation": self.designation,
                "qualification": self.qualification,
                "joined": self.joined,
                "office": self.office,
                "bio": self.bio,
            })
        return d


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30))
    name = Column(String(150))
    dept = Column(String(120))
    faculty = Column(String(150))  # teacher's display name, matching frontend's DB.courses shape
    students = Column(Integer, default=0)

    def to_dict(self):
        return {"id": f"c_{self.id}", "code": self.code, "name": self.name, "dept": self.dept,
                "faculty": self.faculty, "students": self.students}


class SubjectRequest(Base):
    __tablename__ = "subject_requests"
    id = Column(Integer, primary_key=True, index=True)
    teacher_name = Column(String(150))
    code = Column(String(30))
    name = Column(String(150))
    dept = Column(String(120))
    notes = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending | approved | rejected
    reject_reason = Column(Text, nullable=True)
    ts = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": f"sr_{self.id}", "teacherName": self.teacher_name, "code": self.code, "name": self.name,
                "dept": self.dept, "notes": self.notes or "", "status": self.status,
                "rejectReason": self.reject_reason or "", "ts": int(self.ts.timestamp() * 1000)}


class Fee(Base):
    __tablename__ = "fees"
    id = Column(Integer, primary_key=True, index=True)
    student = Column(String(150))  # student display name, matching frontend's DB.fees shape
    total = Column(Float, default=0)
    paid = Column(Float, default=0)
    status = Column(String(20), default="overdue")  # paid | partial | overdue

    def to_dict(self):
        return {"id": f"f_{self.id}", "student": self.student, "total": self.total, "paid": self.paid, "status": self.status}


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String(30))
    course_label = Column(String(150))
    date = Column(String(20))
    marked_by = Column(String(150))
    ts = Column(DateTime, default=datetime.utcnow)
    records = relationship("AttendanceRecord", backref="session", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": f"att_{self.id}", "courseId": self.course_id, "courseLabel": self.course_label,
                "date": self.date, "markedBy": self.marked_by, "ts": int(self.ts.timestamp() * 1000),
                "records": [r.to_dict() for r in self.records]}


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id"))
    student_id = Column(Integer)  # numeric users.id (not the "u_" prefixed display id)
    present = Column(Boolean, default=False)
    confidence = Column(Float, nullable=True)

    def to_dict(self):
        return {"studentId": f"u_{self.student_id}", "present": bool(self.present), "confidence": self.confidence}


class GradeRecord(Base):
    __tablename__ = "grade_records"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String(30))
    course_label = Column(String(150))
    assessment = Column(String(120))
    published_by = Column(String(150))
    ts = Column(DateTime, default=datetime.utcnow)
    entries = relationship("GradeEntry", backref="grade", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": f"grd_{self.id}", "courseId": self.course_id, "courseLabel": self.course_label,
                "assessment": self.assessment, "publishedBy": self.published_by, "ts": int(self.ts.timestamp() * 1000),
                "entries": [e.to_dict() for e in self.entries]}


class GradeEntry(Base):
    __tablename__ = "grade_entries"
    id = Column(Integer, primary_key=True, index=True)
    grade_id = Column(Integer, ForeignKey("grade_records.id"))
    student_id = Column(Integer)
    score = Column(Float)

    def to_dict(self):
        return {"studentId": f"u_{self.student_id}", "score": self.score}


class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    course = Column(String(150))
    due = Column(String(50))
    status = Column(String(20), default="pending")
    submitted_count = Column(Integer, default=0)
    total_students = Column(Integer, default=0)

    def to_dict(self):
        return {"id": f"a_{self.id}", "title": self.title, "course": self.course, "due": self.due,
                "status": self.status, "submittedCount": self.submitted_count, "totalStudents": self.total_students}


class StudyMaterial(Base):
    __tablename__ = "study_materials"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    course = Column(String(150))
    type = Column(String(20))
    uploaded_by = Column(String(150))
    ts = Column(DateTime, default=datetime.utcnow)
    size = Column(String(30), nullable=True)

    def to_dict(self):
        return {"id": f"mat_{self.id}", "title": self.title, "course": self.course, "type": self.type,
                "uploadedBy": self.uploaded_by, "ts": int(self.ts.timestamp() * 1000), "size": self.size}


class ClassNotice(Base):
    __tablename__ = "class_notices"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    course = Column(String(150))
    sent_by = Column(String(150))
    ts = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": f"cn_{self.id}", "title": self.title, "course": self.course, "sentBy": self.sent_by,
                "ts": int(self.ts.timestamp() * 1000)}


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True, index=True)
    applicant = Column(String(150))
    role = Column(String(20))
    type = Column(String(50))
    from_date = Column(String(20))
    to_date = Column(String(20))
    reason = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    ts = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": f"lv_{self.id}", "applicant": self.applicant, "role": self.role, "type": self.type,
                "from": self.from_date, "to": self.to_date, "reason": self.reason or "",
                "status": self.status, "ts": int(self.ts.timestamp() * 1000)}


class Grievance(Base):
    __tablename__ = "grievances"
    id = Column(Integer, primary_key=True, index=True)
    raised_by = Column(String(150))
    role = Column(String(20))
    category = Column(String(100))
    description = Column(Text)
    status = Column(String(20), default="open")  # open | in-review | resolved
    assigned_to = Column(String(150), nullable=True)
    ts = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": f"grv_{self.id}", "raisedBy": self.raised_by, "role": self.role, "category": self.category,
                "description": self.description, "status": self.status, "assignedTo": self.assigned_to,
                "ts": int(self.ts.timestamp() * 1000)}


class AuditLogEntry(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String(150))
    actor_role = Column(String(20))
    action = Column(String(150))
    detail = Column(Text, nullable=True)
    ts = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": f"log_{self.id}", "actor": self.actor, "actorRole": self.actor_role, "action": self.action,
                "detail": self.detail or "", "ts": int(self.ts.timestamp() * 1000)}


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    to_role = Column(String(20))  # broadcast target — matches frontend's pushNotification({toRole,...})
    title = Column(String(200))
    body = Column(Text)
    ts = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)

    def to_dict(self):
        return {"id": f"ntf_{self.id}", "toRole": self.to_role, "title": self.title, "body": self.body,
                "ts": int(self.ts.timestamp() * 1000), "read": bool(self.read)}


class Placement(Base):
    __tablename__ = "placements"
    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(150))
    role = Column(String(150))
    package = Column(String(50))
    location = Column(String(120))
    min_cgpa = Column(Float, default=0)
    min_attendance = Column(Float, default=0)
    deadline = Column(String(50))
    posted_by = Column(String(150))
    status = Column(String(20), default="open")
    ts = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": f"pl_{self.id}", "company": self.company, "role": self.role, "package": self.package,
                "location": self.location, "minCGPA": self.min_cgpa, "minAttendance": self.min_attendance,
                "deadline": self.deadline, "postedBy": self.posted_by, "status": self.status,
                "ts": int(self.ts.timestamp() * 1000)}


class PlacementApplication(Base):
    __tablename__ = "placement_applications"
    id = Column(Integer, primary_key=True, index=True)
    placement_id = Column(String(30))
    student_id = Column(String(30))
    student_name = Column(String(150))
    id_label = Column(String(50))
    status = Column(String(30), default="applied")
    ts = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": f"papp_{self.id}", "placementId": self.placement_id, "studentId": self.student_id,
                "studentName": self.student_name, "idLabel": self.id_label, "status": self.status,
                "ts": int(self.ts.timestamp() * 1000)}


class LibraryBook(Base):
    __tablename__ = "library_books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    author = Column(String(150))
    category = Column(String(120), nullable=True)
    isbn = Column(String(50), nullable=True)
    copies = Column(Integer, default=1)

    def to_dict(self):
        return {"id": f"bk_{self.id}", "title": self.title, "author": self.author, "category": self.category,
                "isbn": self.isbn, "copies": self.copies}


class LibraryRequest(Base):
    __tablename__ = "library_requests"
    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String(150))
    book_id = Column(String(30))
    title = Column(String(200))
    status = Column(String(30), default="pending")  # pending | ready-for-pickup | waitlisted
    ts = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": f"lib_{self.id}", "studentName": self.student_name, "bookId": self.book_id,
                "title": self.title, "status": self.status, "ts": int(self.ts.timestamp() * 1000)}
