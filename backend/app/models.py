from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum
from .database import Base




class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20))
    cv_path = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    interviews = relationship("Interview", back_populates="candidate")
    status = Column(String(50), default="Applied")



class CandidateStatus(str, Enum):
    APPLIED = "Applied"
    TO_INTERVIEW = "To Interview"
    WAITING_CONFIRMATION = "Waiting Confirmation"
    INTERVIEW_SCHEDULED = "Interview Scheduled"
    HIRED = "Hired"
    REJECTED = "Rejected"



class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    department = Column(String(100))
    description = Column(Text)
    required_skills = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    interviews = relationship("Interview", back_populates="job")

class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)

    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"))

    status = Column(String(50), default="Pending")
    score = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    token = Column(String(255), unique=True, nullable=True)  # ← NEW LINE
    scheduled_at = Column(DateTime, nullable=True)  # ← NEW LINE
    available_slots = Column(JSON, nullable=True)




    candidate = relationship("Candidate", back_populates="interviews")
    job = relationship("Job", back_populates="interviews")
   
  
class InterviewStatus(str, Enum):
    PENDING = "Pending"
    AWAITING_CONFIRMATION = "Awaiting Confirmation"
    SCHEDULED = "Scheduled"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"    
  
