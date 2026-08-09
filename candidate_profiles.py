from src.vector_store import initialize_curriculum_vector_store
from src.ingestion import CandidateManager

# 1. Test curriculum vector store initialization
vector_store = initialize_curriculum_vector_store("data/curriculum.json")
print("Curriculum successfully loaded into ChromaDB!")

# 2. Test candidate manager lookup
candidate_mgr = CandidateManager("data/candidate_profiles.json")
sample_candidate = candidate_mgr.get_candidate("cand_123")
print("Loaded candidate profile:", sample_candidate)