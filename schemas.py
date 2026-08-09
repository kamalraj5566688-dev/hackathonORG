from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    session_id: str
    candidate_id: str
    message: str

class InterviewStateModel(BaseModel):
    questions_asked: int
    days_covered: List[int]
    is_completed: bool

class FeedbackReport(BaseModel):
    technical_depth_score: int = Field(..., description="Score from 1 to 10")
    system_design_score: int = Field(..., description="Score from 1 to 10")
    communication_score: int = Field(..., description="Score from 1 to 10")
    strengths: List[str]
    areas_for_improvement: List[str]
    recommended_review_days: List[int]

class ChatResponse(BaseModel):
    session_id: str
    agent_message: str
    interview_state: InterviewStateModel
    feedback: Optional[FeedbackReport] = None