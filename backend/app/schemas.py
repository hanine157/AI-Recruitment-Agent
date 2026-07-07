from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from typing import List, Optional, Literal
from datetime import datetime
from app.models import CandidateStatus, InterviewStatus


# --- CANDIDATE SCHEMAS ---
class CandidateCreate(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "firstName": "John",
                    "lastName": "Doe",
                    "email": "john.doe@example.com",
                    "phone": "12345678",
                    "cvPath": "uploads/john-doe.pdf",
                },
                {
                    "name": "John Doe",
                    "email": "john.doe@example.com",
                },
            ]
        },
    )

    first_name: Optional[str] = Field(default=None, alias="firstName")
    last_name: Optional[str] = Field(default=None, alias="lastName")
    email: EmailStr
    phone: Optional[str] = None
    cv_path: Optional[str] = Field(default=None, alias="cvPath")

    @model_validator(mode="before")
    @classmethod
    def accept_name_field(cls, data):
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        full_name = normalized.get("name") or normalized.get("fullName")
        has_first_name = normalized.get("first_name") or normalized.get("firstName")
        has_last_name = normalized.get("last_name") or normalized.get("lastName")

        if full_name and not has_first_name:
            name_parts = str(full_name).strip().split(maxsplit=1)
            if name_parts:
                normalized["first_name"] = name_parts[0]
                if not has_last_name:
                    normalized["last_name"] = name_parts[1] if len(name_parts) > 1 else "-"

        if not normalized.get("first_name") and not normalized.get("firstName"):
            email = normalized.get("email")
            if email:
                normalized["first_name"] = str(email).split("@", 1)[0]

        if not normalized.get("last_name") and not normalized.get("lastName"):
            normalized["last_name"] = "-"

        return normalized

class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    first_name: str = Field(serialization_alias="firstName")
    last_name: str = Field(serialization_alias="lastName")
    email: str
    phone: Optional[str]
    cv_path: Optional[str] = Field(default=None, serialization_alias="cvPath")
    created_at: datetime
    status: CandidateStatus


class CandidateStatusUpdate(BaseModel):
    status: CandidateStatus
    job_id: int | None = None

# --- JOB SCHEMAS ---

class JobCreate(BaseModel):
    title: str
    department: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[str] = None

class JobResponse(BaseModel):
    id: int
    title: str
    department: Optional[str]
    description: Optional[str]
    required_skills: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# --- INTERVIEW SCHEMAS ---

class InterviewCreate(BaseModel):
    candidate_id: int
    job_id: int

class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate: CandidateResponse
    job: JobResponse
    status: str
    overall_score: Optional[float] = None
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    token: Optional[str] = None
    available_slots: Optional[List[str]] = None

class InterviewStatusUpdate(BaseModel):
    status: InterviewStatus

class InterviewSchedule(BaseModel):
    scheduled_at: datetime
    mode: Literal["slot", "free"]

class AvailabilityUpdate(BaseModel):
    slots: List[datetime]

class InterviewScheduleRequest(BaseModel):
    scheduled_at: datetime
    mode: str  # "slot" or "free"
