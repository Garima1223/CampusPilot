from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List


class SubjectRequestCreate(BaseModel):
    code: str
    name: str
    dept: Optional[str] = "General"
    notes: Optional[str] = ""


class AttendanceRecordIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    student_id: str = Field(alias="studentId")
    present: bool
    confidence: Optional[float] = None


class MarkAttendanceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    course_id: str = Field(alias="courseId")
    course_label: str = Field(alias="courseLabel")
    records: List[AttendanceRecordIn]


class GradeEntryIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    student_id: str = Field(alias="studentId")
    score: float


class PublishGradesRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    course_id: str = Field(alias="courseId")
    course_label: str = Field(alias="courseLabel")
    assessment: str
    entries: List[GradeEntryIn]


class AssignmentCreate(BaseModel):
    title: str
    course: str
    due: str


class MaterialUpload(BaseModel):
    title: str
    course: str
    type: str
    size: Optional[str] = None


class NoticeCreate(BaseModel):
    title: str
    course: str


class LeaveRequestCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: str
    from_date: str = Field(alias="from")
    to_date: str = Field(alias="to")
    reason: Optional[str] = ""


class GrievanceCreate(BaseModel):
    category: str
    description: str
