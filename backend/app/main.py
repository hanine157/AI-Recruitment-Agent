# Load environment variables BEFORE any other imports
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path, override=True)

# Now import the rest
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session
from .database import engine, SessionLocal
from . import models, crud, schemas
from app.schemas import CandidateStatusUpdate
from app.email_service import (
    send_confirmation_email,
    send_email,
    send_interview_email,
    send_recruiter_notification,
)
from ai_agent.ai_service import start_interview, test_groq_connection, test_system_prompt, continue_interview, MAX_QUESTIONS



def ensure_database_schema():
    models.Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE interviews ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMP"))
        connection.execute(text("ALTER TABLE interviews ADD COLUMN IF NOT EXISTS available_slots JSON"))


ensure_database_schema()


app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path == "/candidates":
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Invalid candidate data. Send JSON with at least an email, for example: "
                '{"firstName":"John","lastName":"Doe","email":"john@example.com"}'
            },
        )

    return JSONResponse(status_code=422, content={"detail": exc.errors()})

@app.get("/")
def home():
    return {"message": "Backend is running!"}
@app.get("/test-db")
def test_database():
    try:
        connection = engine.connect()
        connection.close()

        return {
            "message": "Database connected successfully"
        }

    except Exception as e:
        return {
            "error": str(e)
        }
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
        raise HTTPException(
            status_code=409,
            detail="A candidate with this email already exists."
        ) from exc
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





# --- INTERVIEW ROUTES ---

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


@app.patch("/candidates/{candidate_id}/status", response_model=schemas.CandidateResponse)
def update_candidate_status(candidate_id: int, status_update: schemas.CandidateStatusUpdate, db: Session = Depends(get_db)):
    candidate = crud.update_candidate_status(db=db, candidate_id=candidate_id, status=status_update.status)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    if status_update.status == "To Interview":
        job = db.query(models.Job).filter(
    models.Job.id == status_update.job_id
).first()
        if job:
            interview = crud.create_interview_with_token(
                db=db,
                candidate_id=candidate_id,
                job_id=job.id
            )
            try:
                send_interview_email(
                    candidate_email=candidate.email,
                    candidate_name=candidate.first_name,
                    job_title=job.title if job else "the position",
                    interview_token=interview.token
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

Congratulations 🎉

This email was sent successfully from your FastAPI backend.

Your email service is working correctly.
"""
    )
    return {"message": "Test email sent successfully"}


@app.patch("/interviews/{token}/availability")
def set_availability(
    token: str,
    data: schemas.AvailabilityUpdate,
    db: Session = Depends(get_db)
):
    # 1. Find interview by token
    interview = db.query(models.Interview).filter(models.Interview.token == token).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # 2. Convert datetime objects to ISO format (important for JSON storage)
    slots = [slot.isoformat() for slot in data.slots]

    # 3. Save slots in DB
    interview.available_slots = slots

    # 4. Update status
    interview.status = "Waiting Candidate Choice"

    # 5. Save changes
    db.commit()
    db.refresh(interview)

    return {
        "message": "Availability updated successfully",
        "available_slots": interview.available_slots,
        "status": interview.status
    }


# candidate schedules the interview
@app.patch("/interviews/{token}/schedule")
def schedule_interview(
    token: str,
    request: schemas.InterviewScheduleRequest,
    db: Session = Depends(get_db)
):
    try:
        interview = crud.schedule_interview(
            db=db,
            token=token,
            scheduled_at=request.scheduled_at,
            mode=request.mode
        )
        if interview is None:
            raise HTTPException(status_code=404, detail="Interview not found")

        # get candidate
        candidate = db.query(models.Candidate).filter(
            models.Candidate.id == interview.candidate_id
        ).first()

        # automatically confirm regardless of mode
        candidate.status = "Interview Scheduled"
        interview.status = "Scheduled"
        db.commit()

        # send confirmation email to candidate
        send_confirmation_email(
            candidate_email=candidate.email,
            candidate_name=candidate.first_name,
            scheduled_at=request.scheduled_at
        )

        # send notification email to recruiter
        recruiter_email = os.getenv("RECRUITER_EMAIL")
        send_recruiter_notification(
            recruiter_email=recruiter_email,
            candidate_name=f"{candidate.first_name} {candidate.last_name}",
            scheduled_at=request.scheduled_at
        )

        return {
            "message": "Interview scheduled successfully",
            "status": "Scheduled",
            "scheduled_at": request.scheduled_at
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@app.get("/test-ai")
def test_ai():
    return {"response": test_groq_connection()}

@app.get("/test-prompt")
def test_prompt():
    return {"response": test_system_prompt()}



@app.post("/interviews/{token}/start")
def start_interview_route(token: str, db: Session = Depends(get_db)):
    # Step 1: find the interview using the token
    interview = db.query(models.Interview).filter(
        models.Interview.token == token
    ).first()
    
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Step 2: get the job from the database
    job = db.query(models.Job).filter(
        models.Job.id == interview.job_id
    ).first()
    
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Step 3: get the candidate from the database
    candidate = db.query(models.Candidate).filter(
        models.Candidate.id == interview.candidate_id
    ).first()
    
    # Step 4: update interview status to "In Progress"
    interview.status = "In Progress"
    db.commit()
    
    # Step 5: send everything to AI and get first question
    candidate_cv=candidate.cv_text or "No CV provided yet"
    try:
        first_question = start_interview(
            job_title=job.title,
            job_description=job.description,
            required_skills=job.required_skills,
            candidate_cv=candidate_cv,
            candidate_name=f"{candidate.first_name} {candidate.last_name}".strip()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI interview start failed: {exc}") from exc
    
    return {
        "message": "Interview started",
        "candidate": candidate.first_name,
        "job": job.title,
        "first_question": first_question
    }

MAX_QUESTIONS = 25  # hard safety cap

@app.post("/interviews/{token}/message")
def send_message(token: str, payload: schemas.MessageCreate, db: Session = Depends(get_db)):
    interview = db.query(models.Interview).filter(models.Interview.token == token).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    job = db.query(models.Job).filter(models.Job.id == interview.job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    candidate = db.query(models.Candidate).filter(models.Candidate.id == interview.candidate_id).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # 1. Save the candidate's answer
    crud.save_message(
        db=db,
        interview_id=interview.id,
        role="candidate",
        content=payload.content
    )

    # 2. Count how many questions the AI has already asked
    questions_asked = crud.count_ai_questions(db, interview.id)

    # 3. Get full conversation history to send to AI
    history = crud.get_messages(db, interview.id)

    # 4. Ask AI for the next message (you already built this in Day 3/4)
    ai_response = continue_interview(
        job_title=job.title,
        job_description=job.description,
        required_skills=job.required_skills,
        candidate_cv=candidate.cv_text or "No CV provided",
        candidate_name=f"{candidate.first_name} {candidate.last_name}".strip(),
        conversation_history=history,
        force_end=(questions_asked >= MAX_QUESTIONS)
    )

    # 5. Check if this is the end
    interview_ended = "[INTERVIEW_END]" in ai_response
    clean_response = ai_response.replace("[INTERVIEW_END]", "").strip()

    # 6. Save AI's message
    crud.save_message(
        db=db,
        interview_id=interview.id,
        role="ai",
        content=clean_response
    )

    # 7. If ended, update statuses
    if interview_ended:
        interview.status = "Completed"
        candidate.status = "Interview Completed"

    db.commit()

    return {
        "response": clean_response,
        "interview_ended": interview_ended
    }