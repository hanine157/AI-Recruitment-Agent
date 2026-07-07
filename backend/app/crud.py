from sqlalchemy.orm import Session
from . import models, schemas
import json
import uuid
from datetime import datetime


# --- CANDIDATE CRUD ---

def create_candidate(db: Session, candidate: schemas.CandidateCreate):
    db_candidate = models.Candidate(
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        email=candidate.email,
        phone=candidate.phone,
        cv_path=candidate.cv_path
    )
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    return db_candidate

def get_candidates(db: Session):
    return db.query(models.Candidate).all()

def get_candidate(db: Session, candidate_id: int):
    return db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()


def update_candidate_status(db: Session, candidate_id: int, status):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()

    if not candidate:
        return None

    # Accept either an Enum with a `.value` attribute or a plain string
    candidate.status = status.value if hasattr(status, "value") else status

    db.commit()
    db.refresh(candidate)

    return candidate
# --- JOB CRUD ---

def create_job(db: Session, job: schemas.JobCreate):
    db_job = models.Job(
        title=job.title,
        department=job.department,
        description=job.description,
        required_skills=job.required_skills
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_jobs(db: Session):
    return db.query(models.Job).all()


# --- INTERVIEW CRUD ---

def create_interview(db: Session, interview: schemas.InterviewCreate):
    db_interview = models.Interview(
        candidate_id=interview.candidate_id,
        job_id=interview.job_id,
        status="pending"
    )
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    return db_interview

def get_interviews(db: Session):
    return db.query(models.Interview).all()

def get_interview(db: Session, interview_id: int):
    return db.query(models.Interview).filter(models.Interview.id == interview_id).first()

def update_interview_status(db: Session, interview_id: int, status: str):
    interview = db.query(models.Interview).filter(models.Interview.id == interview_id).first()
    if interview:
        interview.status = status
        db.commit()
        db.refresh(interview)
    return interview



def create_interview_with_token(db: Session, candidate_id: int, job_id: int):
    token = str(uuid.uuid4())  # generates a unique token like "a3f8c2d1-9b4e..."
    db_interview = models.Interview(
        candidate_id=candidate_id,
        job_id=job_id,
        status="pending",
        token=token
    )
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    return db_interview


def schedule_interview(db: Session, token: str, scheduled_at: datetime, mode: str):
    interview = db.query(models.Interview).filter(
        models.Interview.token == token
    ).first()

    if not interview:
        return None

    # check if already scheduled
    if interview.status in ["Scheduled", "Awaiting Confirmation"]:
        raise ValueError("Interview is already scheduled")

    # check if date is in the past
    if scheduled_at < datetime.now():
        raise ValueError("Cannot schedule in the past")

    # check working hours
    if scheduled_at.hour < 8 or scheduled_at.hour >= 18:
        raise ValueError("Must be between 08:00 and 18:00")

    if mode == "slot":
        # validate slot exists in available_slots
        raw_slots = interview.available_slots or []
        if isinstance(raw_slots, str):
            try:
                slots = json.loads(raw_slots)
            except (TypeError, ValueError):
                slots = []
        elif isinstance(raw_slots, list):
            slots = raw_slots
        else:
            slots = []

        if scheduled_at.isoformat() not in slots:
            raise ValueError("Selected slot is not available")

        # slot mode → automatically scheduled, no confirmation needed
        interview.scheduled_at = scheduled_at
        interview.status = "Scheduled"

    elif mode == "free":
        # free mode → needs recruiter confirmation
        interview.scheduled_at = scheduled_at
        interview.status = "Awaiting Confirmation"

    db.commit()
    db.refresh(interview)
    return interview

