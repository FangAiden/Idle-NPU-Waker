import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

from app.config import DATA_DIR, SESSIONS_DB_PATH


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, dict] = {}
        self.current_session_id: Optional[str] = None
        self.temp_sessions: Dict[str, dict] = {}  # 临时会话存储

        self.db_path = Path(SESSIONS_DB_PATH)
        self._init_db()
        self._migrate_from_json()
        self._load_sessions()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    is_temporary INTEGER DEFAULT 0,
                    created_at REAL,
                    updated_at REAL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    created_at REAL,
                    meta TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    session_id TEXT,
                    name TEXT,
                    kind TEXT,
                    mime TEXT,
                    content TEXT,
                    truncated INTEGER DEFAULT 0,
                    size INTEGER DEFAULT 0,
                    FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                """
            )

    def _get_state(self, conn: sqlite3.Connection, key: str) -> Optional[str]:
        row = conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def _set_state(self, conn: sqlite3.Connection, key: str, value: Optional[str]) -> None:
        if value:
            conn.execute(
                "INSERT INTO app_state(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
        else:
            conn.execute("DELETE FROM app_state WHERE key = ?", (key,))

    def _infer_attachment_kind(self, attachment: dict) -> str:
        kind = str(attachment.get("kind") or "").strip().lower()
        if not kind:
            mime = str(attachment.get("mime") or "").strip().lower()
            content = str(attachment.get("content") or "")
            if mime.startswith("image/") or content.startswith("data:image/"):
                kind = "image"
            else:
                kind = "text"
        return kind

    def _attachment_size(self, content: str, kind: str) -> int:
        if not content:
            return 0
        if kind == "image" and content.startswith("data:"):
            try:
                header, b64 = content.split(",", 1)
                if "base64" in header:
                    import base64
                    raw = base64.b64decode(b64, validate=False)
                    return len(raw)
            except Exception:
                return len(content.encode("utf-8", errors="ignore"))
        return len(content.encode("utf-8", errors="ignore"))

    def _insert_message(
        self,
        conn: sqlite3.Connection,
        session_id: str,
        role: str,
        content: str,
        meta: Optional[dict],
        attachments: Optional[List[dict]],
    ) -> None:
        created_at = time.time()
        meta_json = json.dumps(meta, ensure_ascii=False) if meta else None
        cursor = conn.execute(
            "INSERT INTO messages(session_id, role, content, created_at, meta) VALUES(?, ?, ?, ?, ?)",
            (session_id, role, content, created_at, meta_json),
        )
        message_id = cursor.lastrowid
        if attachments:
            for att in attachments:
                name = str(att.get("name") or "").strip()
                content_val = str(att.get("content") or "")
                if not name or not content_val:
                    continue
                kind = self._infer_attachment_kind(att)
                mime = str(att.get("mime") or "")
                truncated = 1 if att.get("truncated") else 0
                size = self._attachment_size(content_val, kind)
                conn.execute(
                    """
                    INSERT INTO attachments(message_id, session_id, name, kind, mime, content, truncated, size)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (message_id, session_id, name[:200], kind, mime, content_val, truncated, size),
                )
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (created_at, session_id),
        )

    def _load_messages(self, conn: sqlite3.Connection, sid: str) -> List[dict]:
        rows = conn.execute(
            "SELECT id, role, content, meta FROM messages WHERE session_id = ? ORDER BY id ASC",
            (sid,),
        ).fetchall()
        attachments_rows = conn.execute(
            """
            SELECT message_id, name, kind, mime, content, truncated
            FROM attachments WHERE session_id = ?
            ORDER BY id ASC
            """,
            (sid,),
        ).fetchall()
        attachments_map: Dict[int, List[dict]] = {}
        for row in attachments_rows:
            attachments_map.setdefault(row["message_id"], []).append(
                {
                    "name": row["name"] or "",
                    "content": row["content"] or "",
                    "truncated": bool(row["truncated"]),
                    "kind": row["kind"] or "",
                    "mime": row["mime"] or "",
                }
            )

        history: List[dict] = []
        for row in rows:
            msg = {"role": row["role"], "content": row["content"]}
            if row["meta"]:
                try:
                    extra = json.loads(row["meta"])
                    if isinstance(extra, dict):
                        msg.update(extra)
                except Exception:
                    pass
            if row["id"] in attachments_map:
                msg["attachments"] = attachments_map[row["id"]]
            history.append(msg)
        return history

    def _migrate_from_json(self) -> None:
        legacy_path = Path(DATA_DIR) / "sessions.json"
        if not legacy_path.exists():
            return
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS cnt FROM sessions").fetchone()["cnt"]
            if count:
                return
            try:
                data = json.loads(legacy_path.read_text(encoding="utf-8"))
            except Exception:
                return
            sessions = data.get("sessions", {})
            now = time.time()
            for sid, payload in sessions.items():
                title = payload.get("title") or "New Chat"
                conn.execute(
                    "INSERT INTO sessions(id, title, is_temporary, created_at, updated_at) VALUES(?, ?, 0, ?, ?)",
                    (sid, title, now, now),
                )
                for msg in payload.get("history", []):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    attachments = msg.get("attachments") if isinstance(msg.get("attachments"), list) else []
                    meta = {k: v for k, v in msg.items() if k not in ("role", "content", "attachments")}
                    self._insert_message(conn, sid, role, content, meta, attachments)
            current_sid = data.get("current_session_id")
            self._set_state(conn, "current_session_id", current_sid)
            try:
                legacy_path.rename(legacy_path.with_suffix(".json.bak"))
            except Exception:
                pass

    def _load_sessions(self) -> None:
        self.sessions = {}
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, title, is_temporary FROM sessions WHERE is_temporary = 0 ORDER BY updated_at DESC"
            ).fetchall()
            for row in rows:
                self.sessions[row["id"]] = {
                    "title": row["title"] or "",
                    "history": [],
                    "is_temporary": False,
                }
            current_sid = self._get_state(conn, "current_session_id")
            if current_sid and current_sid in self.sessions:
                self.current_session_id = current_sid

    def _save_sessions(self):
        with self._connect() as conn:
            self._set_state(conn, "current_session_id", self.current_session_id)

    def create_session(self, title="New Chat", is_temporary=False) -> str:
        sid = str(uuid.uuid4())
        session_data = {"title": title, "history": [], "is_temporary": is_temporary}

        if is_temporary:
            self.temp_sessions[sid] = session_data
        else:
            now = time.time()
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO sessions(id, title, is_temporary, created_at, updated_at) VALUES(?, ?, 0, ?, ?)",
                    (sid, title, now, now),
                )
            self.sessions[sid] = session_data

        self.current_session_id = sid
        self._save_sessions()
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
            with self._connect() as conn:
                conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))
            del self.sessions[sid]
            if self.current_session_id == sid:
                self.current_session_id = None
            self._save_sessions()

    def get_session(self, sid: str):
        if sid in self.temp_sessions:
            return self.temp_sessions.get(sid)
        if sid not in self.sessions:
            return None
        with self._connect() as conn:
            history = self._load_messages(conn, sid)
        data = dict(self.sessions.get(sid, {}))
        data["history"] = history
        return data

    def get_current_history(self) -> List[dict]:
        if self.current_session_id:
            if self.current_session_id in self.temp_sessions:
                return self.temp_sessions[self.current_session_id]["history"]
            if self.current_session_id in self.sessions:
                with self._connect() as conn:
                    return self._load_messages(conn, self.current_session_id)
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

        attachments = kwargs.get("attachments") if kwargs else None
        meta = {k: v for k, v in msg.items() if k not in ("role", "content", "attachments")}

        if target_sid in self.temp_sessions:
            self.temp_sessions[target_sid]["history"].append(msg)
        elif target_sid in self.sessions:
            with self._connect() as conn:
                self._insert_message(conn, target_sid, role, content, meta, attachments)

    def update_title(self, title: str, sid: str = None) -> str:
        target_sid = sid or self.current_session_id
        short_title = title[:30] + ("..." if len(title) > 30 else "")

        if target_sid in self.temp_sessions:
            self.temp_sessions[target_sid]["title"] = short_title
            return short_title
        elif target_sid in self.sessions:
            with self._connect() as conn:
                conn.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                             (short_title, time.time(), target_sid))
            self.sessions[target_sid]["title"] = short_title
            return short_title
        return title

    def rename_session(self, sid: str, new_title: str):
        """手动重命名会话"""
        if sid in self.temp_sessions:
            self.temp_sessions[sid]["title"] = new_title
        elif sid in self.sessions:
            with self._connect() as conn:
                conn.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                             (new_title, time.time(), sid))
            self.sessions[sid]["title"] = new_title

    def _message_id_for_index(self, conn: sqlite3.Connection, sid: str, index: int) -> Optional[int]:
        row = conn.execute(
            "SELECT id FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT 1 OFFSET ?",
            (sid, index),
        ).fetchone()
        return row["id"] if row else None

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
            with self._connect() as conn:
                msg_id = self._message_id_for_index(conn, target_sid, index)
                if msg_id is None:
                    return False
                conn.execute("UPDATE messages SET content = ? WHERE id = ?", (content, msg_id))
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
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT id FROM messages WHERE session_id = ? ORDER BY id ASC",
                    (target_sid,),
                ).fetchall()
                ids = [row["id"] for row in rows]
                if end_index > len(ids):
                    end_index = len(ids)
                ids_to_delete = ids[end_index:]
                if ids_to_delete:
                    placeholders = ",".join("?" for _ in ids_to_delete)
                    conn.execute(
                        f"DELETE FROM messages WHERE id IN ({placeholders})",
                        ids_to_delete,
                    )
            return True
        return False

    def clear_session(self, sid: str) -> bool:
        return self.truncate_history(0, sid=sid)

    def get_session_size(self, sid: str) -> Optional[int]:
        if sid in self.temp_sessions:
            history = self.temp_sessions[sid].get("history", [])
            return self._estimate_history_size(history)
        if sid not in self.sessions:
            return None
        with self._connect() as conn:
            msg_bytes = conn.execute(
                "SELECT COALESCE(SUM(LENGTH(CAST(content AS BLOB))), 0) AS total FROM messages WHERE session_id = ?",
                (sid,),
            ).fetchone()["total"]
            att_bytes = conn.execute(
                "SELECT COALESCE(SUM(size), 0) AS total FROM attachments WHERE session_id = ?",
                (sid,),
            ).fetchone()["total"]
        return int(msg_bytes or 0) + int(att_bytes or 0)

    def _estimate_history_size(self, history: List[dict]) -> int:
        total = 0
        for msg in history:
            content = msg.get("content", "")
            total += len(str(content).encode("utf-8", errors="ignore"))
            attachments = msg.get("attachments") or []
            for att in attachments:
                kind = self._infer_attachment_kind(att)
                total += self._attachment_size(str(att.get("content") or ""), kind)
        return total
