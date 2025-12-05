import uuid
from typing import Dict, List, Optional

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, dict] = {}
        self.current_session_id: Optional[str] = None

    def create_session(self, title="New Chat") -> str:
        sid = str(uuid.uuid4())
        self.sessions[sid] = {"title": title, "history": []}
        self.current_session_id = sid
        return sid

    def delete_session(self, sid: str):
        if sid in self.sessions:
            del self.sessions[sid]
            if self.current_session_id == sid:
                self.current_session_id = None

    def get_session(self, sid: str):
        return self.sessions.get(sid)

    def get_current_history(self) -> List[dict]:
        if self.current_session_id and self.current_session_id in self.sessions:
            return self.sessions[self.current_session_id]["history"]
        return []

    def add_message(self, role: str, content: str, sid: str = None):
        target_sid = sid or self.current_session_id
        if target_sid and target_sid in self.sessions:
            self.sessions[target_sid]["history"].append({"role": role, "content": content})

    def update_title(self, title: str, sid: str = None) -> str:
        target_sid = sid or self.current_session_id
        if target_sid and target_sid in self.sessions:
            short_title = title[:20] + ("..." if len(title) > 20 else "")
            self.sessions[target_sid]["title"] = short_title
            return short_title
        return title