from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class LoginRequest(BaseModel):
    email: str
    password: str
    # The portal the person picked on the login form. Frontend parity: if
    # present, it must match the account's real role or the login is
    # rejected (closes the "log into any portal with any valid creds" hole).
    role: Optional[str] = None


class SignupRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    email: str
    password: str
    role: str  # "student" | "teacher" — admin is deliberately rejected server-side, see auth_router
    id_label: Optional[str] = Field(default=None, alias="idLabel")


class UserCreateByAdmin(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    email: str
    role: str
    id_label: Optional[str] = Field(default=None, alias="idLabel")
    department: Optional[str] = None
    designation: Optional[str] = None
    phone: Optional[str] = None


class UserStatusUpdate(BaseModel):
    status: str  # "active" | "inactive"


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    phone: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    qualification: Optional[str] = None
    office: Optional[str] = None
    bio: Optional[str] = None
