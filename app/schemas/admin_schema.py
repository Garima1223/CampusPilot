from pydantic import BaseModel
from typing import Optional


class CourseCreate(BaseModel):
    code: str
    name: str
    dept: str
    faculty: str


class SubjectRejectRequest(BaseModel):
    reason: Optional[str] = ""


class GrievanceAssignRequest(BaseModel):
    assignee: str
