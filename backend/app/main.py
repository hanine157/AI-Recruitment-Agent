# Load environment variables before any app imports.
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .cv_service import extract_text_from_pdf, save_uploaded_file
from .database import SessionLocal, engine
from .email_service import (
    send_confirmation_email,
    send_email,
    send_interview_email,
    send_recruiter_notification,
)
from ai_agent.ai_service import (
    MAX_QUESTIONS,
    continue_interview,
    start_interview,
    test_groq_connection,
    test_system_prompt,
)

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path, override=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_database_schema() -> None:
    models.Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE interviews ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMP"))
        connection.execute(text("ALTER TABLE interviews ADD COLUMN IF NOT EXISTS available_slots JSON"))


ensure_database_schema()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path == "/candidates":
        return JSONResponse(
            status_code=400,
            content={
                "detail": (
                    "Invalid candidate data. Send JSON with at least an email, "
                    'for example: {"firstName":"John","lastName":"Doe","email":"john@example.com"}'
                )
            },
        )

    errors = exc.errors()
    for err in errors:
        ctx = err.get("ctx")
        if isinstance(ctx, dict) and isinstance(ctx.get("error"), Exception):
            ctx["error"] = str(ctx["error"])

    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/")
def home():
    return {"message": "Backend is running!"}


@app.get("/test-db")
def test_database():
    try:
        connection = engine.connect()
        connection.close()
        return {"message": "Database connected successfully"}
    except Exception as exc:
        return {"error": str(exc)}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/candidates", response_model=schemas.CandidateResponse)
def create_candidate(candidate: schemas.CandidateCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_candidate(db=db, candidate=candidate)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A candidate with this email already exists.") from exc
    except ProgrammingError as exc:
        db.rollback()
        if "UndefinedTable" not in str(exc) and "does not exist" not in str(exc):
            raise

        models.Base.metadata.create_all(bind=engine)
        return crud.create_candidate(db=db, candidate=candidate)


@app.get("/candidates", response_model=list[schemas.CandidateResponse])
def get_all_candidates(db: Session = Depends(get_db)):
    return crud.get_candidates(db=db)


@app.get("/candidates/{candidate_id}", response_model=schemas.CandidateResponse)
def get_one_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = crud.get_candidate(db=db, candidate_id=candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@app.post("/jobs", response_model=schemas.JobResponse)
def create_job(job: schemas.JobCreate, db: Session = Depends(get_db)):
    return crud.create_job(db=db, job=job)


@app.get("/jobs", response_model=list[schemas.JobResponse])
def get_all_jobs(db: Session = Depends(get_db)):
    return crud.get_jobs(db=db)


@app.post("/interviews", response_model=schemas.InterviewResponse)
def create_interview(interview: schemas.InterviewCreate, db: Session = Depends(get_db)):
    return crud.create_interview(db=db, interview=interview)


@app.get("/interviews", response_model=list[schemas.InterviewResponse])
def get_all_interviews(db: Session = Depends(get_db)):
    return crud.get_interviews(db=db)


@app.get("/interviews/{interview_id}", response_model=schemas.InterviewResponse)
def get_one_interview(interview_id: int, db: Session = Depends(get_db)):
    interview = crud.get_interview(db=db, interview_id=interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


@app.put("/interviews/{interview_id}/status", response_model=schemas.InterviewResponse)
def update_status(interview_id: int, status_update: schemas.InterviewStatusUpdate, db: Session = Depends(get_db)):
    interview = crud.update_interview_status(db=db, interview_id=interview_id, status=status_update.status)
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


@app.get("/interviews/token/{token}", response_model=schemas.InterviewResponse)
def get_interview_by_token(token: str, db: Session = Depends(get_db)):
    interview = db.query(models.Interview).filter(models.Interview.token == token).first()
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


@app.post("/interviews/{token}/face-metrics")
def save_face_metrics(token: str, metric: schemas.FaceMetricCreate, db: Session = Depends(get_db)):
    interview = db.query(models.Interview).filter(models.Interview.token == token).first()
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    crud.save_face_metric(
        db=db,
        interview_id=interview.id,
        eye_contact=metric.eye_contact,
        expression=metric.expression,
        attention_level=metric.attention_level
    )

    return {"message": "Face metric saved"}

@app.patch("/candidates/{candidate_id}/status", response_model=schemas.CandidateResponse)
def update_candidate_status(
    candidate_id: int,
    status_update: schemas.CandidateStatusUpdate,
    db: Session = Depends(get_db),
):
    candidate = crud.update_candidate_status(db=db, candidate_id=candidate_id, status=status_update.status)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if status_update.status == schemas.CandidateStatus.TO_INTERVIEW:
        if status_update.job_id is None:
            raise HTTPException(status_code=400, detail="job_id is required when moving a candidate to interview.")

        job = db.query(models.Job).filter(models.Job.id == status_update.job_id).first()
        if job:
            existing_interview = db.query(models.Interview).filter(
                models.Interview.candidate_id == candidate_id,
                models.Interview.job_id == job.id,
            ).first()

            if existing_interview:
                interview = existing_interview
            else:
                interview = crud.create_interview_with_token(
                    db=db,
                    candidate_id=candidate_id,
                    job_id=job.id,
                )

            try:
                send_interview_email(
                    candidate_email=candidate.email,
                    candidate_name=candidate.first_name,
                    job_title=job.title,
                    interview_token=interview.token,
                )
            except Exception as exc:
                print(f"Interview email was not sent: {exc}")

    return candidate


@app.post("/test-email")
def test_email():
    send_email(
        to_email="projectrecrutement1@gmail.com",
        subject="FastAPI Email Test",
        body="""
Hello!

Congratulations!

This email was sent successfully from your FastAPI backend.

Your email service is working correctly.
""",
    )
    return {"message": "Test email sent successfully"}


@app.patch("/interviews/{token}/availability")
def set_availability(token: str, data: schemas.AvailabilityUpdate, db: Session = Depends(get_db)):
    interview = db.query(models.Interview).filter(models.Interview.token == token).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    slots = [slot.isoformat() for slot in data.slots]
    interview.available_slots = slots
    interview.status = "Waiting Candidate Choice"

    db.commit()
    db.refresh(interview)

    return {
        "message": "Availability updated successfully",
        "available_slots": interview.available_slots,
        "status": interview.status,
    }


@app.patch("/interviews/{token}/schedule")
def schedule_interview(
    token: str,
    request: schemas.InterviewScheduleRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        interview = crud.schedule_interview(
            db=db,
            token=token,
            scheduled_at=request.scheduled_at,
            mode=request.mode,
        )
        if interview is None:
            raise HTTPException(status_code=404, detail="Interview not found")

        candidate = db.query(models.Candidate).filter(models.Candidate.id == interview.candidate_id).first()
        job = db.query(models.Job).filter(models.Job.id == interview.job_id).first()

        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate not found")
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")

        candidate.status = "Interview Scheduled"
        interview.status = "Scheduled"
        db.commit()

        def send_emails():
            try:
                send_confirmation_email(
                    candidate_email=candidate.email,
                    candidate_name=candidate.first_name,
                    scheduled_at=request.scheduled_at,
                    job_title=job.title,
                    token=interview.token,
                )
            except Exception as exc:
                print(f"Confirmation email failed: {exc}")

            try:
                recruiter_email = os.getenv("RECRUITER_EMAIL")
                if recruiter_email:
                    send_recruiter_notification(
                        recruiter_email=recruiter_email,
                        candidate_name=f"{candidate.first_name} {candidate.last_name}",
                        scheduled_at=request.scheduled_at,
                    )
            except Exception as exc:
                print(f"Recruiter notification failed: {exc}")

        background_tasks.add_task(send_emails)

        return {
            "message": "Interview scheduled successfully",
            "status": "Scheduled",
            "scheduled_at": request.scheduled_at,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/test-ai")
def test_ai():
    return {"response": test_groq_connection()}


@app.get("/test-prompt")
def test_prompt():
    return {"response": test_system_prompt()}


@app.post("/interviews/{token}/start")
def start_interview_route(token: str, db: Session = Depends(get_db)):
    interview = db.query(models.Interview).filter(models.Interview.token == token).first()
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")

    job = db.query(models.Job).filter(models.Job.id == interview.job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    candidate = db.query(models.Candidate).filter(models.Candidate.id == interview.candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if interview.scheduled_at:
        now = datetime.now(ZoneInfo("Africa/Tunis"))
        scheduled = interview.scheduled_at

        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=ZoneInfo("Africa/Tunis"))

        start_window = scheduled - timedelta(minutes=10)
        end_window = scheduled + timedelta(hours=2)

        if now < start_window:
            raise HTTPException(
                status_code=403,
                detail=f"The interview is not available yet. It will open at {start_window.strftime('%d/%m/%Y %H:%M')}.",
            )

        if now > end_window:
            raise HTTPException(status_code=403, detail="This interview link has expired.")

    existing_messages = crud.get_messages(db, interview.id)
    if existing_messages:
        first_ai_message = next((m for m in existing_messages if m.role == "ai"), None)
        return {
            "message": "Interview already started",
            "candidate": candidate.first_name,
            "job": job.title,
            "first_question": first_ai_message.content if first_ai_message else None,
        }

    interview.status = "In Progress"
    candidate.status = "In Progress"
    db.commit()

    candidate_cv = candidate.cv_text or "No CV provided yet"
    try:
        first_question = start_interview(
            job_title=job.title,
            job_description=job.description,
            required_skills=job.required_skills,
            candidate_cv=candidate_cv,
            candidate_name=f"{candidate.first_name} {candidate.last_name}".strip(),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI interview start failed: {exc}") from exc

    crud.save_message(
        db=db,
        interview_id=interview.id,
        role="ai",
        content=first_question,
    )
    db.commit()

    return {
        "message": "Interview started",
        "candidate": candidate.first_name,
        "job": job.title,
        "first_question": first_question,
    }


@app.post("/interviews/{token}/message")
def send_message(token: str, payload: schemas.MessageCreate, db: Session = Depends(get_db)):
    interview = db.query(models.Interview).filter(models.Interview.token == token).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview.status == "Completed":
        raise HTTPException(
            status_code=400,
            detail="This interview has already been completed. No further messages can be sent.",
        )

    job = db.query(models.Job).filter(models.Job.id == interview.job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    candidate = db.query(models.Candidate).filter(models.Candidate.id == interview.candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    crud.save_message(
        db=db,
        interview_id=interview.id,
        role="candidate",
        content=payload.content,
    )

    questions_asked = crud.count_ai_questions(db, interview.id)
    history = crud.get_messages(db, interview.id)

    ai_response = continue_interview(
        job_title=job.title,
        job_description=job.description,
        required_skills=job.required_skills,
        candidate_cv=candidate.cv_text or "No CV provided",
        candidate_name=f"{candidate.first_name} {candidate.last_name}".strip(),
        conversation_history=history,
        force_end=(questions_asked >= MAX_QUESTIONS),
    )

    interview_ended = "[INTERVIEW_END]" in ai_response
    clean_response = ai_response.replace("[INTERVIEW_END]", "").strip()

    crud.save_message(
        db=db,
        interview_id=interview.id,
        role="ai",
        content=clean_response,
    )

    if interview_ended:
        interview.status = "Completed"
        candidate.status = "Interview Completed"

    db.commit()

    return {"response": clean_response, "interview_ended": interview_ended}


@app.post("/candidates/{candidate_id}/cv")
async def upload_cv(candidate_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    file_content = await file.read()
    filename = f"candidate_{candidate_id}_cv.pdf"
    file_path = save_uploaded_file(file_content, filename)

    cv_text = extract_text_from_pdf(file_path)
    if not cv_text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    candidate.cv_path = file_path
    candidate.cv_text = cv_text
    db.commit()

    return {
        "message": "CV uploaded successfully",
        "candidate": candidate.first_name,
        "cv_path": file_path,
        "characters_extracted": len(cv_text),
        "cv_preview": cv_text[:200] + "...",
    }
