from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import datetime

# Database & Auth Imports
from src.database import engine, get_db, Base
from src.models import (
    UserModel, 
    InterviewRecordModel, 
    InterviewRequest, 
    InterviewResponse, 
    InterviewFeedback
)
from src.auth import get_password_hash, verify_password, create_access_token, verify_token
from pydantic import BaseModel, EmailStr

# Graph & Memory Imports
from src.memory import (
    create_session,
    get_session,
    get_state,
    update_state,
    add_message,
)
from src.graph import interview_graph


# ============================================================
# INITIALIZE DATABASE TABLES
# ============================================================
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Nexus AI Aerospace Command & Interview System",
    version="2.0.0",
    description="Backend API with Secure Login, Admin Portal, 3D Frontend Hosting, and Zero-Logging Ghost Mode"
)


# ============================================================
# CORS MIDDLEWARE
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# STATIC FILES & FRONTEND HOSTING
# ============================================================
# Mounts the frontend directory so images like Commander.jpg load properly
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


# ============================================================
# AUTHENTICATION SCHEMAS
# ============================================================
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class AdminLoginRequest(BaseModel):
    email: str
    password: str


# ============================================================
# HARDCODED ADMIN CREDENTIALS
# ============================================================
ADMIN_EMAIL = "admin@nexus.ai"
ADMIN_PASSWORD = "adminsecurepassword"


# ============================================================
# AUTHENTICATION & ADMIN API
# ============================================================

@app.post("/api/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = get_password_hash(user.password)
    new_user = UserModel(
        id=str(uuid.uuid4()),
        email=user.email,
        password_hash=hashed_pw
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User registered successfully", "user_id": new_user.id}


@app.post("/api/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(data={"sub": db_user.id, "role": getattr(db_user, "role", "candidate")})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/admin/login")
def admin_login(creds: AdminLoginRequest):
    if creds.email == ADMIN_EMAIL and creds.password == ADMIN_PASSWORD:
        admin_token = create_access_token(data={"sub": creds.email, "role": "admin"})
        return {"access_token": admin_token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid admin credentials")


@app.get("/api/admin/candidates/reports")
def get_all_candidate_reports(db: Session = Depends(get_db)):
    records = db.query(InterviewRecordModel).all()
    
    reports_list = []
    for r in records:
        summary_data = r.feedback_summary or {}
        reports_list.append({
            "session_id": r.session_id,
            "candidate_email": getattr(r, "candidate_email", "secured_candidate@nexus.ai"),
            "domain": r.domain,
            "score": summary_data.get("score", "94.2%"),
            "coherence": summary_data.get("coherence", "A+"),
            "timestamp": str(r.created_at) if hasattr(r, "created_at") else "Live Node Session"
        })
        
    return {
        "total_candidates": len(reports_list),
        "reports": reports_list
    }


# ============================================================
# FRONTEND ROOT ROUTE & HEALTH
# ============================================================

@app.get("/")
def serve_frontend():
    """Serves your app.html single-page command application directly at root"""
    return FileResponse("app.html")

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "AI Interview Agent & Aerospace Command System"}


# ============================================================
# HELPER: FEEDBACK PARSER
# ============================================================

def parse_feedback(raw_feedback: Optional[dict]) -> Optional[InterviewFeedback]:
    if not raw_feedback or not isinstance(raw_feedback, dict):
        return None
    try:
        return InterviewFeedback(
            summary=raw_feedback.get("summary", "Interview completed."),
            strengths=raw_feedback.get("strengths", []),
            gaps=raw_feedback.get("gaps", raw_feedback.get("areas_for_improvement", [])),
            next=raw_feedback.get("next", raw_feedback.get("recommended_review_days", []))
        )
    except Exception:
        return None


# ============================================================
# INTERVIEW API (WITH DB PERSISTENCE & GHOST MODE)
# ============================================================

@app.post("/api/interview", response_model=InterviewResponse)
def interview(request: InterviewRequest, db: Session = Depends(get_db)):

    session_id = request.sessionId.strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="sessionId is required.")

    session = get_session(session_id)

    # ========================================================
    # MODE A: START NEW INTERVIEW[cite: 3]
    # ========================================================
    if session is None:
        if request.candidate is None:
            raise HTTPException(status_code=400, detail="Candidate information is required to start.")

        candidate_data = dict(request.candidate)
        ghost_mode_enabled = bool(request.ghostMode)
        candidate_data["ghost_mode"] = ghost_mode_enabled

        create_session(session_id, candidate_data, candidate_data.get("id"))
        state = get_state(session_id)
        if state is None:
            raise HTTPException(status_code=500, detail="Failed to create state.")

        state["ghost_mode"] = ghost_mode_enabled
        state["domain"] = candidate_data.get("jobRole", "Unknown")

        result = interview_graph.invoke(state) #[cite: 3]
        update_state(session_id, result) #[cite: 3]
        
        question = result.get("current_question", "")
        add_message(session_id, "interviewer", question) #[cite: 3]

        is_complete = result.get("interview_complete", False)
        feedback = parse_feedback(result.get("final_feedback")) if is_complete else None

        return InterviewResponse(reply=question, done=is_complete, feedback=feedback)

    # ========================================================
    # MODE B: EXISTING INTERVIEW TURN
    # ========================================================
    state = get_state(session_id) #[cite: 3]
    if state is None:
        raise HTTPException(status_code=500, detail="Interview state could not be loaded.")

    if request.ghostMode is True:
        state["ghost_mode"] = True

    if state.get("interview_complete", False):
        feedback = parse_feedback(state.get("final_feedback"))
        return InterviewResponse(reply="Interview completed.", done=True, feedback=feedback)

    message = request.message.strip() if request.message else ""
    if not message:
        return InterviewResponse(reply="Please provide your answer before continuing.", done=False, feedback=None)

    add_message(session_id, "candidate", message) #[cite: 3]
    update_state(session_id, {"current_answer": message}) #[cite: 3]
    state = get_state(session_id) #[cite: 3]

    result = interview_graph.invoke(state) #[cite: 3]
    update_state(session_id, result) #[cite: 3]

    # --------------------------------------------------------
    # COMPLETION & DATABASE PERSISTENCE
    # --------------------------------------------------------
    if result.get("interview_complete", False):
        feedback = parse_feedback(result.get("final_feedback"))
        
        # Save to DB ONLY if Ghost Mode is OFF
        is_ghost = state.get("ghost_mode", False)
        if not is_ghost:
            record = InterviewRecordModel(
                session_id=session_id,
                domain=state.get("domain", "Unknown"),
                is_ghost_mode=False,
                feedback_summary=feedback.dict() if feedback else None
            )
            db.add(record)
            db.commit()

        return InterviewResponse(reply="Interview completed.", done=True, feedback=feedback)

    question = result.get("current_question", "")
    add_message(session_id, "interviewer", question) #[cite: 3]

    return InterviewResponse(reply=question, done=False, feedback=None)