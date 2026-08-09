
from typing import TypedDict, List, Dict, Any


class InterviewState(TypedDict, total=False):

    # ============================================================
    # CANDIDATE
    # ============================================================

    candidate_id: str

    candidate_profile: Dict[str, Any]

    # ============================================================
    # INTERVIEW CONTROL
    # ============================================================

    current_phase: str

    # Current curriculum day being tested
    current_day: int

    # Number of PRIMARY questions generated
    questions_asked_count: int

    # Maximum number of PRIMARY questions
    max_questions: int

    # Number of candidate answers processed
    answers_received_count: int

    # ============================================================
    # FOLLOW-UP CONTROL
    # ============================================================

    # Number of follow-ups used for the CURRENT primary question.
    #
    # 0 = no follow-up has been asked
    # 1 = one follow-up has already been asked
    #
    # This prevents endless follow-up loops.
    followups_used_for_current_question: int

    # Maximum follow-ups allowed for each primary question.
    max_followups_per_question: int

    # ============================================================
    # CURRICULUM COVERAGE
    # ============================================================

    curriculum_days_covered: List[int]

    target_days: List[int]

    # ============================================================
    # CURRENT INTERACTION
    # ============================================================

    current_question: str

    current_answer: str

    # "primary" or "followup"
    current_question_type: str

    # ============================================================
    # CONVERSATION
    # ============================================================

    conversation_history: List[Dict[str, Any]]

    # Questions already asked.
    # Used to prevent duplicate questions.
    asked_questions: List[str]

    # ============================================================
    # RAG
    # ============================================================

    retrieved_context: List[str]

    # ============================================================
    # ANSWER EVALUATION
    # ============================================================

    answer_analysis: Dict[str, Any]

    # ============================================================
    # INTERVIEW STATUS
    # ============================================================

    interview_complete: bool

    # ============================================================
    # FINAL FEEDBACK
    # ============================================================

    final_feedback: Dict[str, Any]

    # ============================================================
    # GRAPH ROUTING
    # ============================================================

    route: str
