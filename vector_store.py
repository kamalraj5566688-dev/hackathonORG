import os
import json

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings


# ============================================================
# LOCAL EMBEDDING MODEL
# ============================================================

embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5"
)


# ============================================================
# INITIALIZE CURRICULUM VECTOR STORE
# ============================================================

def initialize_curriculum_vector_store(
    json_path: str,
    persist_directory: str = "./chroma_db"
):
    """
    Load curriculum.json and create/load a local ChromaDB
    vector store.

    Each curriculum day becomes one searchable document.
    """

    # --------------------------------------------------------
    # Check curriculum file
    # --------------------------------------------------------

    if not os.path.exists(json_path):
        raise FileNotFoundError(
            f"Curriculum file not found: {json_path}"
        )

    # --------------------------------------------------------
    # Load existing ChromaDB
    # --------------------------------------------------------

    if (
        os.path.exists(persist_directory)
        and os.listdir(persist_directory)
    ):
        print("Loading existing ChromaDB...")

        return Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )

    print("Creating new ChromaDB...")

    # --------------------------------------------------------
    # Load Curriculum JSON
    # --------------------------------------------------------

    with open(
        json_path,
        "r",
        encoding="utf-8-sig"
    ) as f:
        curriculum_data = json.load(f)

    # --------------------------------------------------------
    # Validate curriculum structure
    # --------------------------------------------------------

    if not isinstance(curriculum_data, dict):
        raise ValueError(
            "curriculum.json must contain a JSON object."
        )

    days = curriculum_data.get("days", [])

    if not days:
        raise ValueError(
            "No curriculum days found in curriculum.json."
        )

    print(f"Found {len(days)} curriculum days.")

    # --------------------------------------------------------
    # Convert curriculum days into documents
    # --------------------------------------------------------

    documents = []

    for day_item in days:

        day = day_item.get("day", "")
        title = day_item.get("title", "")
        content_type = day_item.get("type", "")

        tools = day_item.get("tools", [])
        objectives = day_item.get("objectives", [])

        # Ensure lists are actually lists
        if not isinstance(tools, list):
            tools = [str(tools)]

        if not isinstance(objectives, list):
            objectives = [str(objectives)]

        # ----------------------------------------------------
        # Convert lists to readable text
        # ----------------------------------------------------

        tools_text = ", ".join(
            str(tool) for tool in tools
        )

        objectives_text = "\n".join(
            f"- {objective}"
            for objective in objectives
        )

        # ----------------------------------------------------
        # Create searchable document
        # ----------------------------------------------------

        content = f"""
Day: {day}

Title:
{title}

Type:
{content_type}

Tools:
{tools_text}

Learning Objectives:
{objectives_text}
""".strip()

        documents.append(
            Document(
                page_content=content,
                metadata={
                    "day": (
                        int(day)
                        if str(day).isdigit()
                        else str(day)
                    ),
                    "title": title,
                    "type": content_type
                }
            )
        )

    # --------------------------------------------------------
    # Create ChromaDB
    # --------------------------------------------------------

    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_directory
    )

    print(
        f"Indexed {len(documents)} curriculum days."
    )

    return vector_store


# ============================================================
# SEARCH CURRICULUM
# ============================================================

def search_curriculum(
    vector_store,
    query: str,
    k: int = 3
):
    """
    Perform semantic search against the curriculum.
    """

    if not query or not query.strip():
        return []

    results = vector_store.similarity_search(
        query.strip(),
        k=k
    )

    return results