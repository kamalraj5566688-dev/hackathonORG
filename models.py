import datetime
from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey
from src.database import Base

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# ============================================================
# DATABASE MODELS (SQLAlchemy)
# ============================================================

class UserModel(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="candidate") # candidate, recruiter, admin
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class InterviewRecordModel(Base):
    __tablename__ = "interview_records"
    
    session_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    domain = Column(String, nullable=False)
    is_ghost_mode = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    feedback_summary = Column(JSON, nullable=True) # Remains NULL if ghost mode was active


# ============================================================
# FINAL INTERVIEW FEEDBACK
# ============================================================

class InterviewFeedback(BaseModel):

    summary: str = Field(
        description="Overall assessment summary"
    )

    strengths: List[str] = Field(
        default_factory=list,
        description="List of identified candidate strengths"
    )

    gaps: List[str] = Field(
        default_factory=list,
        description="Specific domain or skill gaps identified"
    )

    next: List[str] = Field(
        default_factory=list,
        description="Actionable recommendations and next steps"
    )

    # Optional Scores (Used for Dashboard Analytics)
    overall_score: Optional[int] = Field(
        default=None,
        ge=1,
        le=10
    )

    technical_knowledge: Optional[int] = Field(
        default=None,
        ge=1,
        le=10
    )

    system_design: Optional[int] = Field(
        default=None,
        ge=1,
        le=10
    )

    communication: Optional[int] = Field(
        default=None,
        ge=1,
        le=10
    )

    # Backward compatibility fields
    areas_for_improvement: Optional[List[str]] = Field(
        default_factory=list
    )

    recommended_review_days: Optional[List[Any]] = Field(
        default_factory=list
    )


# ============================================================
# API REQUEST
# ============================================================

class InterviewRequest(BaseModel):

    # Session identifier
    sessionId: str

    # Candidate ID can be supplied separately
    candidate_id: Optional[str] = None

    # Candidate answer
    message: Optional[str] = None

    # Candidate profile — required when starting
    candidate: Optional[Dict[str, Any]] = None

    # Ghost Mode flag (Zero-Logging Privacy Feature)
    ghostMode: Optional[bool] = Field(
        default=False,
        description="When set to True, no session logs or feedback will be saved to the database"
    )


# ============================================================
# API RESPONSE
# ============================================================

class InterviewResponse(BaseModel):

    reply: str

    done: bool

    # Feedback is only available when the interview is complete
    feedback: Optional[InterviewFeedback] = None