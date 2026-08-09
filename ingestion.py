import json


class CandidateManager:
    """
    Loads and manages candidate profiles from candidate_profiles.json.
    """

    def __init__(self, profiles_path: str):

        with open(profiles_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        candidates = data.get("candidates", [])

        self.profiles = {
            candidate["member"]["id"]: candidate
            for candidate in candidates
            if "member" in candidate and "id" in candidate["member"]
        }

    # ---------------------------------------------------------
    # Get complete candidate profile
    # ---------------------------------------------------------

    def get_candidate(self, candidate_id: str):

        return self.profiles.get(candidate_id)

    # ---------------------------------------------------------
    # Get basic member information
    # ---------------------------------------------------------

    def get_member(self, candidate_id: str):

        candidate = self.get_candidate(candidate_id)

        if not candidate:
            return None

        return candidate.get("member", {})

    # ---------------------------------------------------------
    # Get candidate name
    # ---------------------------------------------------------

    def get_name(self, candidate_id: str):

        member = self.get_member(candidate_id)

        if not member:
            return None

        return member.get("name")

    # ---------------------------------------------------------
    # Get candidate job role
    # ---------------------------------------------------------

    def get_job_role(self, candidate_id: str):

        member = self.get_member(candidate_id)

        if not member:
            return None

        return member.get("jobRole")

    # ---------------------------------------------------------
    # Get all missions
    # ---------------------------------------------------------

    def get_missions(self, candidate_id: str):

        candidate = self.get_candidate(candidate_id)

        if not candidate:
            return []

        return candidate.get("missions", [])

    # ---------------------------------------------------------
    # Get completed days
    # ---------------------------------------------------------

    def get_completed_days(self, candidate_id: str):

        missions = self.get_missions(candidate_id)

        return [
            mission["day"]
            for mission in missions
            if mission.get("passed") is True
        ]

    # ---------------------------------------------------------
    # Get failed days
    # ---------------------------------------------------------

    def get_failed_days(self, candidate_id: str):

        missions = self.get_missions(candidate_id)

        return [
            mission["day"]
            for mission in missions
            if mission.get("passed") is False
        ]

    # ---------------------------------------------------------
    # Get skipped days
    # ---------------------------------------------------------

    def get_skipped_days(self, candidate_id: str):

        missions = self.get_missions(candidate_id)

        return [
            mission["day"]
            for mission in missions
            if mission.get("skipped") is True
        ]

    # ---------------------------------------------------------
    # Get completed mission titles
    # ---------------------------------------------------------

    def get_completed_missions(self, candidate_id: str):

        missions = self.get_missions(candidate_id)

        return [
            mission["title"]
            for mission in missions
            if mission.get("passed") is True
        ]

    # ---------------------------------------------------------
    # Get failed mission titles
    # ---------------------------------------------------------

    def get_failed_missions(self, candidate_id: str):

        missions = self.get_missions(candidate_id)

        return [
            mission["title"]
            for mission in missions
            if mission.get("passed") is False
        ]

    # ---------------------------------------------------------
    # Get skipped mission titles
    # ---------------------------------------------------------

    def get_skipped_missions(self, candidate_id: str):

        missions = self.get_missions(candidate_id)

        return [
            mission["title"]
            for mission in missions
            if mission.get("skipped") is True
        ]

    # ---------------------------------------------------------
    # Get high-attempt missions
    # ---------------------------------------------------------

    def get_high_attempt_missions(
        self,
        candidate_id: str,
        threshold: int = 3
    ):

        missions = self.get_missions(candidate_id)

        return [
            {
                "day": mission.get("day"),
                "title": mission.get("title"),
                "attempts": mission.get("attempts")
            }
            for mission in missions
            if mission.get("attempts", 0) >= threshold
            and mission.get("passed") is True
        ]

    # ---------------------------------------------------------
    # Get strong areas
    # ---------------------------------------------------------

    def get_strong_areas(self, candidate_id: str):

        missions = self.get_missions(candidate_id)

        return [
            mission.get("title")
            for mission in missions
            if mission.get("passed") is True
            and mission.get("attempts", 99) <= 1
        ]

    # ---------------------------------------------------------
    # Get weak areas
    # ---------------------------------------------------------

    def get_weak_areas(self, candidate_id: str):

        missions = self.get_missions(candidate_id)

        weak_areas = []

        for mission in missions:

            # Explicit failure
            if mission.get("passed") is False:
                weak_areas.append(mission.get("title"))

            # Passed but required multiple attempts
            elif mission.get("attempts", 0) >= 3:
                weak_areas.append(mission.get("title"))

        return weak_areas

    # ---------------------------------------------------------
    # Get skipped areas
    # ---------------------------------------------------------

    def get_skipped_areas(self, candidate_id: str):

        return self.get_skipped_missions(candidate_id)

    # ---------------------------------------------------------
    # Get candidate signals
    # ---------------------------------------------------------

    def get_signals(self, candidate_id: str):

        candidate = self.get_candidate(candidate_id)

        if not candidate:
            return {}

        return candidate.get("signals", {})

    # ---------------------------------------------------------
    # Get clean context for LLM
    # ---------------------------------------------------------

    def get_candidate_context(self, candidate_id: str):

        candidate = self.get_candidate(candidate_id)

        if not candidate:
            return None

        member = candidate.get("member", {})

        return {
            "id": member.get("id"),
            "name": member.get("name"),
            "jobRole": member.get("jobRole"),
            "yearsExperience": member.get("yearsExperience"),
            "education": member.get("education"),
            "status": member.get("status"),

            "completedMissions": self.get_completed_missions(
                candidate_id
            ),

            "failedMissions": self.get_failed_missions(
                candidate_id
            ),

            "skippedMissions": self.get_skipped_missions(
                candidate_id
            ),

            "strongAreas": self.get_strong_areas(
                candidate_id
            ),

            "weakAreas": self.get_weak_areas(
                candidate_id
            ),

            "skippedAreas": self.get_skipped_areas(
                candidate_id
            ),

            "highAttemptMissions": self.get_high_attempt_missions(
                candidate_id
            ),

            "signals": self.get_signals(
                candidate_id
            )
        }

    # ---------------------------------------------------------
    # Alias for LLM context
    # ---------------------------------------------------------

    def get_llm_context(self, candidate_id: str):

        return self.get_candidate_context(candidate_id)