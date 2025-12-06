import uuid
import json
import os
import sys
from typing import Dict, List, Optional

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, dict] = {}
        self.current_session_id: Optional[str] = None
        
        # 确定存储路径
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        self.storage_path = os.path.join(base_dir, "sessions.json")
        self._load_sessions()

    def _load_sessions(self):
        """从文件加载会话"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sessions = data.get("sessions", {})
                    # 恢复 current_session_id，如果存在的话
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
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save sessions: {e}")

    def create_session(self, title="New Chat") -> str:
        sid = str(uuid.uuid4())
        self.sessions[sid] = {"title": title, "history": []}
        self.current_session_id = sid
        self._save_sessions()
        return sid

    def delete_session(self, sid: str):
        if sid in self.sessions:
            del self.sessions[sid]
            if self.current_session_id == sid:
                self.current_session_id = None
            self._save_sessions()

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
            self._save_sessions()

    def update_title(self, title: str, sid: str = None) -> str:
        target_sid = sid or self.current_session_id
        if target_sid and target_sid in self.sessions:
            # 如果标题太长，截断它
            short_title = title[:30] + ("..." if len(title) > 30 else "")
            self.sessions[target_sid]["title"] = short_title
            self._save_sessions()
            return short_title
        return title
        
    def rename_session(self, sid: str, new_title: str):
        """手动重命名会话"""
        if sid in self.sessions:
            self.sessions[sid]["title"] = new_title
            self._save_sessions()