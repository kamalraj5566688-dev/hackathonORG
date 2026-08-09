from langgraph.graph import StateGraph, END

from src.state import InterviewState

from src.agent import (
    router,
    generate_first_question,
    analyze_answer,
    generate_followup_question,
    generate_next_question,
    validate_interview,
    generate_final_feedback,
)


# ============================================================
# ROUTER NODE
# ============================================================

def router_node(state: InterviewState):
    """
    Convert router decision into a state update.
    """

    route = router(state)

    return {
        "route": route
    }


# ============================================================
# BUILD GRAPH
# ============================================================

graph_builder = StateGraph(InterviewState)


# ============================================================
# NODES
# ============================================================

graph_builder.add_node(
    "router",
    router_node
)

graph_builder.add_node(
    "generate_first_question",
    generate_first_question
)

graph_builder.add_node(
    "analyze_answer",
    analyze_answer
)

graph_builder.add_node(
    "generate_followup_question",
    generate_followup_question
)

graph_builder.add_node(
    "generate_next_question",
    generate_next_question
)

graph_builder.add_node(
    "validate_interview",
    validate_interview
)

graph_builder.add_node(
    "generate_final_feedback",
    generate_final_feedback
)


# ============================================================
# ENTRY
# ============================================================

graph_builder.set_entry_point(
    "router"
)


# ============================================================
# MAIN ROUTER
# ============================================================

def route_from_router(
    state: InterviewState
):

    return state.get(
        "route",
        "generate_first_question"
    )


graph_builder.add_conditional_edges(
    "router",
    route_from_router,
    {
        "generate_first_question":
            "generate_first_question",

        "analyze_answer":
            "analyze_answer",

        "generate_final_feedback":
            "generate_final_feedback",

        "generate_next_question":
            "generate_next_question",
    }
)


# ============================================================
# FIRST QUESTION
# ============================================================

graph_builder.add_edge(
    "generate_first_question",
    END
)


# ============================================================
# ANSWER ANALYSIS
# ============================================================

def route_after_analysis(
    state: InterviewState
):
    """
    Decide what happens after evaluating an answer.

    IMPORTANT:

    If the answer belonged to a follow-up question,
    analyze_answer() sets current_phase to QUESTIONING.

    Therefore the follow-up can NEVER create another
    follow-up.

    Primary answer:
        weak/incomplete -> FOLLOW_UP
        good            -> validate

    Follow-up answer:
        always          -> validate
    """

    question_type = state.get(
        "current_question_type",
        "primary"
    )

    phase = state.get(
        "current_phase",
        "QUESTIONING"
    )

    # --------------------------------------------------------
    # FOLLOW-UP ANSWER
    #
    # A follow-up has already been used.
    # Never generate another follow-up.
    # --------------------------------------------------------

    if question_type == "followup":

        return "validate_interview"

    # --------------------------------------------------------
    # PRIMARY ANSWER NEEDS FOLLOW-UP
    # --------------------------------------------------------

    if phase == "FOLLOW_UP":

        return "generate_followup_question"

    # --------------------------------------------------------
    # PRIMARY ANSWER IS ACCEPTABLE
    # --------------------------------------------------------

    return "validate_interview"


graph_builder.add_conditional_edges(
    "analyze_answer",
    route_after_analysis,
    {
        "generate_followup_question":
            "generate_followup_question",

        "validate_interview":
            "validate_interview",
    }
)


# ============================================================
# FOLLOW-UP QUESTION
# ============================================================

graph_builder.add_edge(
    "generate_followup_question",
    END
)


# ============================================================
# VALIDATE INTERVIEW
# ============================================================

def route_after_validation(
    state: InterviewState
):

    if state.get(
        "interview_complete",
        False
    ):

        return "generate_final_feedback"

    return "generate_next_question"


graph_builder.add_conditional_edges(
    "validate_interview",
    route_after_validation,
    {
        "generate_final_feedback":
            "generate_final_feedback",

        "generate_next_question":
            "generate_next_question",
    }
)


# ============================================================
# NEXT PRIMARY QUESTION
# ============================================================

graph_builder.add_edge(
    "generate_next_question",
    END
)


# ============================================================
# FINAL FEEDBACK
# ============================================================

graph_builder.add_edge(
    "generate_final_feedback",
    END
)


# ============================================================
# COMPILE
# ============================================================

interview_graph = graph_builder.compile()