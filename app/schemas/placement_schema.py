from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class PlacementCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    company: str
    role: str
    package: str
    location: str
    min_cgpa: float = Field(alias="minCGPA")
    min_attendance: float = Field(alias="minAttendance")
    deadline: str


class ApplicationStatusUpdate(BaseModel):
    status: str
