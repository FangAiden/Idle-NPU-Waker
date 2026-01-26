import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from app.config import DATA_DIR

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, dict] = {}
        self.current_session_id: Optional[str] = None
        self.temp_sessions: Dict[str, dict] = {}  # 临时会话存储

        base_dir = Path(DATA_DIR)
        self.storage_path = base_dir / "sessions.json"
        self._load_sessions()

    def _load_sessions(self):
        """从文件加载会话"""
        if self.storage_path.exists():
            try:
                with self.storage_path.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sessions = data.get("sessions", {})
                    last_sid = data.get("current_session_id")
                    if last_sid and last_sid in self.sessions:
                        self.current_session_id = last_sid
            except Exception as e:
                print(f"Failed to load sessions: {e}")

    def _save_sessions(self):
        """保存会话到文件"""
        data = {
            "sessions": self.sessions,
            "current_session_id": self.current_session_id
        }
        try:
            with self.storage_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save sessions: {e}")

    def create_session(self, title="New Chat", is_temporary=False) -> str:
        sid = str(uuid.uuid4())
        session_data = {"title": title, "history": [], "is_temporary": is_temporary}

        if is_temporary:
            self.temp_sessions[sid] = session_data
        else:
            self.sessions[sid] = session_data
            self._save_sessions()

        self.current_session_id = sid
        return sid

    def is_temporary_session(self, sid: str = None) -> bool:
        """检查会话是否是临时会话"""
        target_sid = sid or self.current_session_id
        return target_sid in self.temp_sessions

    def delete_session(self, sid: str):
        if sid in self.temp_sessions:
            del self.temp_sessions[sid]
            if self.current_session_id == sid:
                self.current_session_id = None
            return

        if sid in self.sessions:
            del self.sessions[sid]
            if self.current_session_id == sid:
                self.current_session_id = None
            self._save_sessions()

    def get_session(self, sid: str):
        if sid in self.temp_sessions:
            return self.temp_sessions.get(sid)
        return self.sessions.get(sid)

    def get_current_history(self) -> List[dict]:
        if self.current_session_id:
            if self.current_session_id in self.temp_sessions:
                return self.temp_sessions[self.current_session_id]["history"]
            if self.current_session_id in self.sessions:
                return self.sessions[self.current_session_id]["history"]
        return []

    def add_message(self, role: str, content: str, sid: str = None, **kwargs):
        """
        添加消息到历史记录
        :param kwargs: 用于存储额外信息，如 think_duration
        """
        target_sid = sid or self.current_session_id
        if not target_sid:
            return

        msg = {"role": role, "content": content}
        if kwargs:
            msg.update(kwargs)

        if target_sid in self.temp_sessions:
            self.temp_sessions[target_sid]["history"].append(msg)
        elif target_sid in self.sessions:
            self.sessions[target_sid]["history"].append(msg)
            self._save_sessions()

    def update_title(self, title: str, sid: str = None) -> str:
        target_sid = sid or self.current_session_id
        short_title = title[:30] + ("..." if len(title) > 30 else "")

        if target_sid in self.temp_sessions:
            self.temp_sessions[target_sid]["title"] = short_title
            return short_title
        elif target_sid in self.sessions:
            self.sessions[target_sid]["title"] = short_title
            self._save_sessions()
            return short_title
        return title

    def rename_session(self, sid: str, new_title: str):
        """手动重命名会话"""
        if sid in self.temp_sessions:
            self.temp_sessions[sid]["title"] = new_title
        elif sid in self.sessions:
            self.sessions[sid]["title"] = new_title
            self._save_sessions()

    def edit_message(self, index: int, content: str, sid: str = None) -> bool:
        target_sid = sid or self.current_session_id
        if not target_sid:
            return False

        if target_sid in self.temp_sessions:
            history = self.temp_sessions[target_sid].get("history", [])
            if index < 0 or index >= len(history):
                return False
            history[index]["content"] = content
            return True
        elif target_sid in self.sessions:
            history = self.sessions[target_sid].get("history", [])
            if index < 0 or index >= len(history):
                return False
            history[index]["content"] = content
            self._save_sessions()
            return True
        return False

    def truncate_history(self, end_index: int, sid: str = None) -> bool:
        target_sid = sid or self.current_session_id
        if not target_sid:
            return False

        if end_index < 0:
            end_index = 0

        if target_sid in self.temp_sessions:
            history = self.temp_sessions[target_sid].get("history", [])
            if end_index > len(history):
                end_index = len(history)
            self.temp_sessions[target_sid]["history"] = history[:end_index]
            return True
        elif target_sid in self.sessions:
            history = self.sessions[target_sid].get("history", [])
            if end_index > len(history):
                end_index = len(history)
            self.sessions[target_sid]["history"] = history[:end_index]
            self._save_sessions()
            return True
        return False
