from src.state import InterviewState

from src.vector_store import (
    initialize_curriculum_vector_store,
    search_curriculum,
)

from src.llm import ask_llm

import json
import re
import random


# ============================================================
# CONFIGURATION
# ============================================================

MIN_QUESTIONS = 8
MIN_CURRICULUM_DAYS = 4
ROLLING_TURNS = 10

# Maximum follow-ups allowed for ONE primary question
MAX_FOLLOWUPS_PER_QUESTION = 1


# ============================================================
# DOMAIN-SPECIFIC FRAMEWORKS & CONSTRAINTS
# ============================================================

DOMAIN_FRAMEWORKS = {
    "Human Resources (HR)": "Include realistic HR constraints involving labor law compliance, performance improvement plans (PIPs), or talent mapping frameworks like the 9-Box Grid. Introduce hypothetical employee data or turnover percentages.",
    "IT / Software Engineering": "Require the candidate to consider system scalability, latency trade-offs, security vulnerabilities, or specific architecture patterns (e.g., Microservices vs. Monolith).",
    "Management": "Include constraints involving cross-functional stakeholder conflicts, tight budget limitations, risk mitigation, or KPI/OKR tracking.",
    "Marketing": "Require the use of specific data metrics like Customer Acquisition Cost (CAC), Return on Ad Spend (ROAS), conversion rate optimization (CRO), or A/B testing methodologies.",
    "Data Science": "Introduce scenarios with dirty/missing data, model overfitting constraints, or require the candidate to explain statistical significance and model ROI to non-technical executives."
}


# ============================================================
# INITIALIZE RAG
# ============================================================

vector_store = initialize_curriculum_vector_store(
    "data/curriculum.json"
)


# ============================================================
# HELPERS
# ============================================================

def get_candidate_topics(profile):
    """
    Determine candidate's strongest available topics.
    """

    skills = profile.get("skills", [])

    if skills:
        return skills

    strong_areas = profile.get("strongAreas", [])

    if strong_areas:
        return strong_areas

    completed = profile.get("completedMissions", [])

    if completed:
        return completed

    return ["software development"]


def get_completed_topics(profile):
    return profile.get(
        "completedMissions",
        []
    )


def get_skipped_topics(profile):
    return profile.get(
        "skippedMissions",
        []
    )


def extract_day_from_document(document):
    """
    Extract curriculum day from metadata/content.
    """

    metadata = getattr(
        document,
        "metadata",
        {}
    ) or {}

    for key in [
        "day",
        "day_number",
        "curriculum_day",
    ]:

        value = metadata.get(key)

        if value is not None:

            try:
                return int(value)

            except (
                ValueError,
                TypeError
            ):
                pass

    text = getattr(
        document,
        "page_content",
        ""
    )

    patterns = [
        r"Day\s*(\d+)",
        r"DAY\s*(\d+)",
        r"day_number[\"']?\s*[:=]\s*(\d+)",
        r"day[\"']?\s*[:=]\s*(\d+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            return int(
                match.group(1)
            )

    return None


def retrieve_curriculum(
    query,
    k=3
):
    """
    Retrieve relevant curriculum documents.
    """

    documents = search_curriculum(
        vector_store,
        query,
        k=k
    )

    context = "\n\n".join(
        doc.page_content
        for doc in documents
    )

    days = []

    for doc in documents:

        day = extract_day_from_document(
            doc
        )

        if (
            day is not None
            and day not in days
        ):

            days.append(day)

    return (
        documents,
        context,
        days
    )


def get_recent_history(state):

    history = state.get(
        "conversation_history",
        []
    )

    return history[-ROLLING_TURNS:]


def history_to_text(history):

    if not history:
        return "No previous conversation."

    lines = []

    for item in history:

        role = item.get(
            "role",
            "unknown"
        )

        message = item.get(
            "message",
            ""
        )

        question_type = item.get(
            "question_type"
        )

        analysis = item.get(
            "analysis"
        )

        if question_type:

            lines.append(
                f"{role.upper()} "
                f"[{question_type.upper()}]: "
                f"{message}"
            )

        else:

            lines.append(
                f"{role.upper()}: {message}"
            )

        if analysis:

            lines.append(
                "ANALYSIS: "
                + json.dumps(
                    analysis
                )
            )

    return "\n".join(lines)


def get_last_candidate_answer(state):
    """
    Retrieve the most recent candidate answer.

    current_answer is intentionally cleared after
    analysis, so conversation_history is the source
    of truth.
    """

    history = state.get(
        "conversation_history",
        []
    )

    for item in reversed(history):

        if item.get("role") == "candidate":

            return item.get(
                "message",
                ""
            )

    return ""


def get_last_interviewer_question(state):
    """
    Retrieve most recent interviewer question.
    """

    history = state.get(
        "conversation_history",
        []
    )

    for item in reversed(history):

        if item.get("role") == "interviewer":

            return item.get(
                "message",
                ""
            )

    return ""


def get_last_primary_question(state):
    """
    Retrieve the most recent PRIMARY question.

    This is important because the most recent interviewer
    message may be a follow-up.
    """

    history = state.get(
        "conversation_history",
        []
    )

    # First try explicitly tagged primary questions.
    for item in reversed(history):

        if (
            item.get("role") == "interviewer"
            and item.get("question_type") == "primary"
        ):

            return item.get(
                "message",
                ""
            )

    # Backward compatibility with old sessions.
    for item in reversed(history):

        if item.get("role") == "interviewer":

            return item.get(
                "message",
                ""
            )

    return ""


def get_last_question_type(state):
    """
    Determine whether the latest interviewer question
    was primary or follow-up.
    """

    history = state.get(
        "conversation_history",
        []
    )

    for item in reversed(history):

        if item.get("role") == "interviewer":

            return item.get(
                "question_type",
                "primary"
            )

    return "primary"


def safe_json_parse(
    response,
    fallback
):

    try:

        parsed = json.loads(
            response
        )

        if isinstance(
            parsed,
            dict
        ):

            return parsed

        return fallback

    except json.JSONDecodeError:

        cleaned = (
            response
            .replace(
                "```json",
                ""
            )
            .replace(
                "```",
                ""
            )
            .strip()
        )

        try:

            parsed = json.loads(
                cleaned
            )

            if isinstance(
                parsed,
                dict
            ):

                return parsed

            return fallback

        except json.JSONDecodeError:

            return fallback


def clean_question(question):

    if not question:
        return ""

    question = (
        question
        .replace(
            "```",
            ""
        )
        .strip()
    )

    question = re.sub(
        r"^(Question|Q)\s*:\s*",
        "",
        question,
        flags=re.IGNORECASE
    )

    return question.strip()


def is_duplicate_question(
    question,
    asked_questions
):

    if not question:
        return True

    normalized = (
        question
        .strip()
        .lower()
    )

    for previous in asked_questions:

        previous_normalized = (
            previous
            .strip()
            .lower()
        )

        # Exact duplicate
        if normalized == previous_normalized:

            return True

        # Similar long question
        if (
            len(normalized) > 50
            and len(previous_normalized) > 50
        ):

            words_a = set(
                normalized.split()
            )

            words_b = set(
                previous_normalized.split()
            )

            if not words_a or not words_b:

                continue

            similarity = (
                len(
                    words_a & words_b
                )
                /
                len(
                    words_a | words_b
                )
            )

            if similarity >= 0.80:

                return True

    return False


def register_question(
    state,
    question
):

    asked_questions = list(
        state.get(
            "asked_questions",
            []
        )
    )

    if (
        question
        and question not in asked_questions
    ):

        asked_questions.append(
            question
        )

    return asked_questions


def append_interviewer_message(
    state,
    history,
    question,
    question_type
):
    """
    Store interviewer question with explicit type.

    This is critical for distinguishing:

    PRIMARY
    FOLLOWUP
    PRIMARY
    FOLLOWUP
    """

    history.append(
        {
            "role": "interviewer",
            "message": question,
            "question_type": question_type,
        }
    )

    return history


# ============================================================
# ROUTER
# ============================================================

def router(
    state: InterviewState
):

    history = state.get(
        "conversation_history",
        []
    )

    # --------------------------------------------------------
    # Brand-new interview
    # --------------------------------------------------------

    if not history:

        return "generate_first_question"

    # --------------------------------------------------------
    # Interview already complete
    # --------------------------------------------------------

    if state.get(
        "interview_complete",
        False
    ):

        return "generate_final_feedback"

    # --------------------------------------------------------
    # New candidate answer exists
    # --------------------------------------------------------

    current_answer = state.get(
        "current_answer",
        ""
    )

    if current_answer.strip():

        return "analyze_answer"

    # --------------------------------------------------------
    # No answer.
    #
    # If state explicitly says FEEDBACK,
    # validate/finalize.
    # --------------------------------------------------------

    if state.get(
        "current_phase"
    ) == "FEEDBACK":

        return "generate_final_feedback"

    # --------------------------------------------------------
    # Continue with next primary question.
    # --------------------------------------------------------

    return "generate_next_question"


# ============================================================
# FIRST QUESTION
# ============================================================

def generate_first_question(
    state: InterviewState
):

    profile = state.get(
        "candidate_profile",
        {}
    )

    name = profile.get(
        "name",
        "Candidate"
    )

    role = profile.get(
        "jobRole",
        "Software Engineer"
    )

    completed_topics = (
        get_completed_topics(
            profile
        )
    )

    skipped_topics = (
        get_skipped_topics(
            profile
        )
    )

    topics = (
        completed_topics
        or get_candidate_topics(
            profile
        )
    )

    random.shuffle(topics)

    query = (
        f"Interview fundamentals "
        f"for {role}. "
        f"Topics: {', '.join(topics[:3])}"
    )

    documents, context, days = (
        retrieve_curriculum(
            query,
            k=3
        )
    )

    selected_day = (
        days[0]
        if days
        else 0
    )

    styles = [
        "a scenario-based architecture/strategy question",
        "a debugging or troubleshooting question",
        "a conceptual question focusing on trade-offs",
        "a practical implementation question"
    ]
    question_style = random.choice(styles)

    domain_rules = DOMAIN_FRAMEWORKS.get(role, "Ensure the scenario tests practical, advanced domain expertise.")

    prompt = f"""
You are an expert Senior Director of {role}. 
You are conducting a professional interview for a candidate applying for a {role} position.

Candidate:
{name}

Role:
{role}

Topics of Interest:
{completed_topics}

(Provided Reference Context - use ONLY if relevant to {role}: {context})

Generate the FIRST interview question.

Rules:
- Ask exactly ONE question.
- The question MUST strictly align with the {role} domain.
- The question MUST be formatted as {question_style}.
- FIELD-SPECIFIC REQUIREMENT: {domain_rules}
- Ignore the reference context completely if it does not match the {role}.
- Test practical reasoning and domain expertise.
- Do not provide the answer.
- Keep it conversational.
- Return ONLY the question.
"""

    question = clean_question(
        ask_llm(prompt)
    )

    if not question:

        question = (
            f"Can you explain one practical "
            f"problem you have solved "
            f"using strategies relevant to "
            f"{role}?"
        )

    asked_questions = register_question(
        state,
        question
    )

    history = list(
        state.get(
            "conversation_history",
            []
        )
    )

    history = append_interviewer_message(
        state,
        history,
        question,
        "primary"
    )

    return {

        "current_question":
            question,

        "current_question_type":
            "primary",

        "current_day":
            selected_day,

        "curriculum_days_covered":
            days,

        "retrieved_context": [
            doc.page_content
            for doc in documents
        ],

        "question_number":
            1,

        "questions_asked_count":
            1,

        "asked_questions":
            asked_questions,

        "conversation_history":
            history,

        "current_phase":
            "QUESTIONING",

        "interview_complete":
            False,

        "current_answer":
            "",

        "answer_analysis":
            {},

        "answers_received_count":
            0,

        "followups_used_for_current_question":
            0,
    }


# ============================================================
# ANSWER ANALYSIS
# ============================================================

def analyze_answer(
    state: InterviewState
):

    question = state.get(
        "current_question",
        ""
    )

    answer = state.get(
        "current_answer",
        ""
    )

    # --------------------------------------------------------
    # Recover question if necessary
    # --------------------------------------------------------

    if not question:

        question = get_last_interviewer_question(
            state
        )

    # --------------------------------------------------------
    # Analyze answer
    # --------------------------------------------------------

    prompt = f"""
You are a senior technical interviewer.

Question:
{question}

Candidate answer:
{answer}

Analyze the answer.

Return ONLY valid JSON:

{{
    "score": 1,
    "technical_correctness": 1,
    "depth": 1,
    "clarity": 1,
    "quality": "weak",
    "needs_followup": true,
    "reason": "short explanation",
    "missing_concepts": ["concept"]
}}

Rules:

- Scores must be from 1 to 10.
- quality must be one of:
  "weak", "moderate", "strong"
- needs_followup should be true if the answer
  is vague, incomplete, incorrect, or lacks depth.
- Be technically specific.
"""

    response = ask_llm(
        prompt
    ).strip()

    analysis = safe_json_parse(
        response,
        {
            "score": 5,
            "technical_correctness": 5,
            "depth": 5,
            "clarity": 5,
            "quality": "moderate",
            "needs_followup": False,
            "reason": response,
            "missing_concepts": [],
        }
    )

    # --------------------------------------------------------
    # Update conversation history
    # --------------------------------------------------------

    history = list(
        state.get(
            "conversation_history",
            []
        )
    )

    # --------------------------------------------------------
    # Make sure interviewer question exists
    # --------------------------------------------------------

    question_exists = any(
        item.get("role") == "interviewer"
        and item.get("message") == question
        for item in history
    )

    if not question_exists:

        history.append(
            {
                "role": "interviewer",
                "message": question,
                "question_type":
                    state.get(
                        "current_question_type",
                        "primary"
                    ),
            }
        )

    # --------------------------------------------------------
    # Attach analysis to existing candidate answer
    # --------------------------------------------------------

    candidate_message_index = None

    for index in range(
        len(history) - 1,
        -1,
        -1
    ):

        item = history[index]

        if (
            item.get("role") == "candidate"
            and item.get("message") == answer
        ):

            candidate_message_index = index

            break

    if candidate_message_index is not None:

        history[
            candidate_message_index
        ] = {
            **history[
                candidate_message_index
            ],
            "analysis": analysis,
        }

    else:

        history.append(
            {
                "role": "candidate",
                "message": answer,
                "analysis": analysis,
            }
        )

    # --------------------------------------------------------
    # Answer counter
    # --------------------------------------------------------

    answers_received = (
        state.get(
            "answers_received_count",
            0
        )
        + 1
    )

    # --------------------------------------------------------
    # Determine current question type
    # --------------------------------------------------------

    current_question_type = state.get(
        "current_question_type",
        get_last_question_type(state)
    )

    # --------------------------------------------------------
    # Follow-up tracking
    # --------------------------------------------------------

    followups_used = state.get(
        "followups_used_for_current_question",
        0
    )

    needs_followup = bool(
        analysis.get(
            "needs_followup",
            False
        )
    )

    # ========================================================
    # PRIMARY QUESTION ANSWER
    # ========================================================

    if current_question_type == "primary":

        if (
            needs_followup
            and
            followups_used
            < MAX_FOLLOWUPS_PER_QUESTION
        ):

            next_phase = "FOLLOW_UP"

        else:

            next_phase = "QUESTIONING"

            followups_used = 0

    # ========================================================
    # FOLLOW-UP ANSWER
    #
    # NEVER create another follow-up.
    # Always progress to PRIMARY.
    # ========================================================

    else:

        next_phase = "QUESTIONING"

        followups_used = 0

    return {

        "answer_analysis":
            analysis,

        "conversation_history":
            history,

        "answers_received_count":
            answers_received,

        "current_phase":
            next_phase,

        "followups_used_for_current_question":
            followups_used,

        # Prevent duplicate analysis
        "current_answer":
            "",
    }


# ============================================================
# FOLLOW-UP QUESTION
# ============================================================

def generate_followup_question(
    state: InterviewState
):

    profile = state.get(
        "candidate_profile",
        {}
    )

    role = profile.get(
        "jobRole",
        "Software Engineer"
    )

    question = state.get(
        "current_question",
        ""
    )

    answer = get_last_candidate_answer(
        state
    )

    analysis = state.get(
        "answer_analysis",
        {}
    )

    history = get_recent_history(
        state
    )

    followups_used = state.get(
        "followups_used_for_current_question",
        0
    )

    # --------------------------------------------------------
    # Hard protection
    # --------------------------------------------------------

    if (
        followups_used
        >= MAX_FOLLOWUPS_PER_QUESTION
    ):

        return {

            "current_question_type":
                "primary",

            "current_phase":
                "QUESTIONING",

            "interview_complete":
                False,

            "current_answer":
                "",

            "followups_used_for_current_question":
                0,
        }

    # --------------------------------------------------------
    # Use the ORIGINAL PRIMARY question.
    # --------------------------------------------------------

    primary_question = get_last_primary_question(
        state
    )

    if not primary_question:

        primary_question = question

    prompt = f"""
You are an expert Senior Director of {role} conducting an interview.

Candidate role:
{role}

Original PRIMARY question:
{primary_question}

Candidate answer:
{answer}

Answer evaluation:
{json.dumps(
    analysis,
    indent=2
)}

Generate ONE targeted follow-up question.

Rules:
- Ask exactly ONE question.
- This is the ONLY follow-up allowed for the current primary question.
- Probe the specific weakness in the answer based on these missing concepts: {json.dumps(analysis.get("missing_concepts", []), indent=2)}
- The follow-up MUST remain highly relevant to the {role} domain.
- Ask HOW, WHY, or WHAT trade-off when appropriate.
- Do not repeat the original question.
- Do not ask multiple questions.
- Return ONLY the question.
"""

    followup = clean_question(
        ask_llm(prompt)
    )

    asked_questions = list(
        state.get(
            "asked_questions",
            []
        )
    )

    # --------------------------------------------------------
    # Retry duplicate
    # --------------------------------------------------------

    for _ in range(2):

        if not is_duplicate_question(
            followup,
            asked_questions
        ):

            break

        retry_prompt = f"""
Generate a completely different targeted follow-up question.

Original PRIMARY question:
{primary_question}

Candidate answer:
{answer}

Missing concepts:
{json.dumps(
    analysis.get(
        "missing_concepts",
        []
    ),
    indent=2
)}

Previous follow-up:
{followup}

Rules:

- Ask exactly ONE question.
- Probe the missing concept relevant to {role}.
- Do not repeat the previous question.
- Do not provide the answer.
- Return ONLY the question.
"""

        followup = clean_question(
            ask_llm(
                retry_prompt
            )
        )

    # --------------------------------------------------------
    # Safety fallback
    # --------------------------------------------------------

    if not followup:

        missing = analysis.get(
            "missing_concepts",
            []
        )

        if missing:

            followup = (
                f"Can you explain how you would "
                f"address {missing[0]} practically in your role?"
            )

        else:

            followup = (
                "Can you give a concrete "
                "example and "
                "explain the trade-offs involved?"
            )

    asked_questions = register_question(
        state,
        followup
    )

    history = list(
        state.get(
            "conversation_history",
            []
        )
    )

    history = append_interviewer_message(
        state,
        history,
        followup,
        "followup"
    )

    return {

        "current_question":
            followup,

        "current_question_type":
            "followup",

        "current_phase":
            "FOLLOW_UP",

        "interview_complete":
            False,

        "asked_questions":
            asked_questions,

        "conversation_history":
            history,

        "followups_used_for_current_question":
            followups_used + 1,

        "current_answer":
            "",
    }


# ============================================================
# NEXT PRIMARY QUESTION
# ============================================================

def generate_next_question(
    state: InterviewState
):

    profile = state.get(
        "candidate_profile",
        {}
    )

    role = profile.get(
        "jobRole",
        "Software Engineer"
    )

    completed_topics = (
        get_completed_topics(
            profile
        )
    )

    skipped_topics = (
        get_skipped_topics(
            profile
        )
    )

    covered_days = list(
        state.get(
            "curriculum_days_covered",
            []
        )
    )

    question_count = state.get(
        "questions_asked_count",
        0
    )

    asked_questions = list(
        state.get(
            "asked_questions",
            []
        )
    )

    history = get_recent_history(
        state
    )

    previous_primary_question = (
        get_last_primary_question(
            state
        )
    )

    previous_answer = (
        get_last_candidate_answer(
            state
        )
    )

    previous_analysis = state.get(
        "answer_analysis",
        {}
    )

    # ========================================================
    # TOPIC STRATEGY
    # ========================================================

    if question_count < 4:

        topic_pool = list(
            completed_topics
        )

    else:

        topic_pool = (
            list(completed_topics)
            +
            list(skipped_topics)
        )

    if not topic_pool:

        topic_pool = get_candidate_topics(
            profile
        )

    random.shuffle(topic_pool)
    topic_pool = topic_pool[:5]

    # ========================================================
    # RETRIEVE CURRICULUM
    # ========================================================

    query = (
        f"Interview curriculum "
        f"for {role}. "
        f"Topics: {', '.join(topic_pool)}"
    )

    documents, context, days = (
        retrieve_curriculum(
            query,
            k=5
        )
    )

    # ========================================================
    # PREFER A NEW CURRICULUM DAY
    # ========================================================

    new_days = [
        day
        for day in days
        if day not in covered_days
    ]

    selected_day = (
        new_days[0]
        if new_days
        else (
            days[0]
            if days
            else 0
        )
    )

    # ========================================================
    # IF RETRIEVAL REPEATS OLD DAYS,
    # STILL ASK A NEW QUESTION
    # ========================================================

    styles = [
        "a system/process design scenario",
        "a critical review or audit-style question",
        "a question comparing two different tools/approaches",
        "a scaling or productionizing question"
    ]
    question_style = random.choice(styles)
    
    domain_rules = DOMAIN_FRAMEWORKS.get(role, "Ensure the scenario tests practical, advanced domain expertise.")

    prompt = f"""
You are an expert Senior Director of {role} conducting an adaptive interview.

Candidate role:
{role}

Topics of Interest:
{completed_topics}

Previously asked questions:
{json.dumps(asked_questions, indent=2)}

Previous PRIMARY question:
{previous_primary_question}

Previous candidate answer:
{previous_answer}

(Provided Reference Context - use ONLY if relevant to {role}: {context})

Generate the NEXT PRIMARY interview question.

IMPORTANT:
This question is a PRIMARY question, not a follow-up.

Rules:
1. Ask exactly ONE question.
2. The question MUST strictly align with the {role} field. 
3. The question MUST be formulated as {question_style}.
4. FIELD-SPECIFIC REQUIREMENT: {domain_rules}
5. The question MUST be substantially different from every previously asked question.
6. Ignore the reference context if it does not match {role}.
7. Do not repeat the same scenario.
8. Do not continue probing the previous answer.
9. Increase difficulty gradually.
10. Do not introduce unrelated topics.
11. Return ONLY the question.
"""

    question = ""

    # ========================================================
    # RETRY DUPLICATES
    # ========================================================

    for _ in range(3):

        candidate_question = clean_question(
            ask_llm(prompt)
        )

        if (
            candidate_question
            and not is_duplicate_question(
                candidate_question,
                asked_questions
            )
        ):

            question = candidate_question

            break

        prompt += f"""

The generated question was invalid because it was
already used or too similar to an existing question.

Generated question:
{candidate_question}

Generate a completely different PRIMARY question.
"""

    # ========================================================
    # FALLBACK
    # ========================================================

    if not question:

        question = (
            f"How would you apply your advanced knowledge "
            f"to build a production-ready solution in {role}, "
            f"and what trade-offs would you consider?"
        )

    # ========================================================
    # REGISTER
    # ========================================================

    asked_questions = register_question(
        state,
        question
    )

    # ========================================================
    # UPDATE COVERED DAYS
    # ========================================================

    updated_days = list(
        covered_days
    )

    if (
        selected_day
        and selected_day not in updated_days
    ):

        updated_days.append(
            selected_day
        )

    # ========================================================
    # STORE PRIMARY QUESTION IN HISTORY
    # ========================================================

    updated_history = list(
        state.get(
            "conversation_history",
            []
        )
    )

    updated_history = append_interviewer_message(
        state,
        updated_history,
        question,
        "primary"
    )

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "current_question":
            question,

        "current_question_type":
            "primary",

        "current_phase":
            "QUESTIONING",

        "retrieved_context": [
            doc.page_content
            for doc in documents
        ],

        "current_day":
            selected_day,

        "curriculum_days_covered":
            updated_days,

        "conversation_history":
            updated_history,

        "questions_asked_count":
            question_count + 1,

        "asked_questions":
            asked_questions,

        "interview_complete":
            False,

        "current_answer":
            "",

        "followups_used_for_current_question":
            0,
    }


# ============================================================
# VALIDATOR
# ============================================================

def validate_interview(
    state: InterviewState
):

    question_count = state.get(
        "questions_asked_count",
        0
    )

    covered_days = state.get(
        "curriculum_days_covered",
        []
    )

    max_questions = state.get(
        "max_questions",
        MIN_QUESTIONS
    )

    # --------------------------------------------------------
    # Minimum primary questions
    # --------------------------------------------------------

    required_questions = min(
        MIN_QUESTIONS,
        max_questions
    )

    questions_satisfied = (
        question_count
        >= required_questions
    )

    # --------------------------------------------------------
    # Curriculum coverage
    # --------------------------------------------------------

    days_satisfied = (
        len(
            set(
                covered_days
            )
        )
        >= MIN_CURRICULUM_DAYS
    )

    # --------------------------------------------------------
    # Complete only when BOTH conditions pass
    # --------------------------------------------------------

    if (
        questions_satisfied
        and days_satisfied
    ):

        return {

            "interview_complete":
                True,

            "current_phase":
                "FEEDBACK",

        }

    return {

        "interview_complete":
            False,

        "current_phase":
            "QUESTIONING",

    }


# ============================================================
# FINAL FEEDBACK
# ============================================================

def generate_final_feedback(
    state: InterviewState
):

    history = state.get(
        "conversation_history",
        []
    )

    transcript = history_to_text(
        history
    )

    covered_days = state.get(
        "curriculum_days_covered",
        []
    )

    prompt = f"""
You are a senior technical interview evaluator.

Complete interview transcript:

{transcript}

Curriculum days covered:
{covered_days}

Return ONLY valid JSON.

Required structure:

{{
    "summary": "Overall assessment",
    "strengths": [
        "Specific strength"
    ],
    "gaps": [
        "Specific technical gap"
    ],
    "next": [
        "Actionable recommendation"
    ]
}}

Rules:

- Base the evaluation ONLY on the interview.
- Be technically specific.
- Do not invent experience.
- "next" must contain actionable recommendations or curriculum days to review.
- Return valid JSON only.
- No markdown.
- No code fences.
"""

    response = ask_llm(
        prompt
    ).strip()

    feedback = safe_json_parse(
        response,
        {
            "summary": "Interview completed, but structural parsing failed.",
            "strengths": [],
            "gaps": [],
            "next": [],
        }
    )

    # Force the strict spec structure and handle potential LLM hallucinations 
    structured_feedback = {
        "summary": str(feedback.get("summary", "")),
        "strengths": feedback.get("strengths", []),
        "gaps": feedback.get("gaps", feedback.get("areas_for_improvement", [])),
        "next": feedback.get("next", feedback.get("recommended_review_days", []))
    }

    return {

        "final_feedback":
            structured_feedback,

        "interview_complete":
            True,

        "current_phase":
            "FEEDBACK",

        "current_answer":
            "",
    }