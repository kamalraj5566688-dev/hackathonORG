from typing import Dict, Any, Optional

from src.state import InterviewState


# ============================================================
# IN-MEMORY SESSION STORE
# ============================================================

sessions: Dict[str, Dict[str, Any]] = {}


# ============================================================
# CREATE SESSION
# ============================================================

def create_session(
    session_id: str,
    candidate: Dict[str, Any],
    candidate_id: Optional[str] = None,
    max_questions: int = 8,
) -> Dict[str, Any]:

    if candidate_id is None:
        candidate_id = candidate.get("id", "")

    initial_state: InterviewState = {

        # ====================================================
        # CANDIDATE
        # ====================================================

        "candidate_id": candidate_id,
        "candidate_profile": candidate,

        # ====================================================
        # INTERVIEW CONTROL
        # ====================================================

        "current_phase": "INTRO",
        "current_day": 0,

        # Number of PRIMARY questions generated
        "questions_asked_count": 0,

        # Maximum PRIMARY questions
        "max_questions": max_questions,

        # Number of candidate answers actually processed
        "answers_received_count": 0,

        # ====================================================
        # CURRICULUM
        # ====================================================

        "curriculum_days_covered": [],
        "target_days": [],

        # ====================================================
        # CURRENT INTERACTION
        # ====================================================

        "current_question": "",
        "current_answer": "",
        "current_question_type": "",

        # ====================================================
        # CONVERSATION
        # ====================================================

        "conversation_history": [],

        # Questions already generated
        "asked_questions": [],

        # ====================================================
        # RAG
        # ====================================================

        "retrieved_context": [],

        # ====================================================
        # ANSWER EVALUATION
        # ====================================================

        "answer_analysis": {},

        # ====================================================
        # INTERVIEW STATUS
        # ====================================================

        "interview_complete": False,

        # ====================================================
        # FINAL FEEDBACK
        # ====================================================

        "final_feedback": {},

        # ====================================================
        # GRAPH ROUTING
        # ====================================================

        "route": "",
    }

    sessions[session_id] = {
        "candidate": candidate,
        "history": [],
        "state": initial_state,
    }

    return sessions[session_id]


# ============================================================
# GET SESSION
# ============================================================

def get_session(
    session_id: str
) -> Optional[Dict[str, Any]]:

    return sessions.get(session_id)


# ============================================================
# GET STATE
# ============================================================

def get_state(
    session_id: str
) -> Optional[InterviewState]:

    session = get_session(session_id)

    if session is None:
        return None

    return session.get("state")


# ============================================================
# UPDATE STATE
# ============================================================

def update_state(
    session_id: str,
    updates: Dict[str, Any]
) -> Optional[InterviewState]:

    session = get_session(session_id)

    if session is None:
        return None

    state = session.get("state")

    if state is None:
        state = {}

    # Apply updates to existing state
    state.update(updates)

    session["state"] = state

    return state


# ============================================================
# REPLACE COMPLETE STATE
# ============================================================

def set_state(
    session_id: str,
    state: InterviewState
) -> Optional[InterviewState]:

    session = get_session(session_id)

    if session is None:
        return None

    session["state"] = state

    return state


# ============================================================
# ADD MESSAGE
# ============================================================

def add_message(
    session_id: str,
    role: str,
    message: str,
    analysis: Optional[Dict[str, Any]] = None,
) -> bool:

    session = get_session(session_id)

    if session is None:
        return False

    # ========================================================
    # MESSAGE OBJECT
    # ========================================================

    message_data: Dict[str, Any] = {
        "role": role,
        "message": message,
    }

    if analysis is not None:
        message_data["analysis"] = analysis

    # ========================================================
    # STORE IN SESSION HISTORY
    # ========================================================

    session["history"].append(
        message_data
    )

    # ========================================================
    # STORE IN LANGGRAPH HISTORY
    # ========================================================

    state = session.get(
        "state",
        {}
    )

    history = state.get(
        "conversation_history",
        []
    )

    history.append(
        message_data
    )

    # Keep recent conversation history
    state["conversation_history"] = history[-20:]

    session["state"] = state

    return True


# ============================================================
# GET HISTORY
# ============================================================

def get_history(
    session_id: str
):

    session = get_session(session_id)

    if session is None:
        return []

    return session.get(
        "history",
        []
    )


# ============================================================
# CLEAR SESSION
# ============================================================

def clear_session(
    session_id: str
) -> bool:

    if session_id not in sessions:
        return False

    del sessions[session_id]

    return True