from typing import Dict, List


class SessionManager:

    def __init__(self):
        self.sessions: Dict[str, List[dict]] = {}

    def create_session(self, session_id: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []

    def get_history(self, session_id: str):
        return self.sessions.get(session_id, [])

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ):
        self.create_session(session_id)

        self.sessions[session_id].append({
            "role": role,
            "content": content
        })

    def clear_session(self, session_id: str):
        self.sessions.pop(session_id, None)

    def session_exists(self, session_id: str):
        return session_id in self.sessions