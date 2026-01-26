import json
import os
import queue
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) in sys.path:
    sys.path.remove(str(BACKEND_DIR))
bad_app = sys.modules.get("app")
if bad_app and getattr(bad_app, "__file__", None) == str(Path(__file__).resolve()):
    del sys.modules["app"]

from app.config import (
    APP_VERSION,
    DEFAULT_CONFIG,
    CONFIG_GROUPS,
    MODELS_DIR,
    DOWNLOAD_CACHE_DIR,
    DATA_DIR,
    MAX_FILE_BYTES,
)
from app.core.runtime import AVAILABLE_DEVICES
from app.core.session import SessionManager
from app.model_configs import (
    PRESET_MODELS,
    MODEL_SPECIFIC_CONFIGS,
    NPU_COLLECTION_MODELS,
    NPU_COLLECTION_URL,
)
from app.utils.config_loader import load_model_json_configs, resolve_supported_setting_keys
from app.utils.scanner import scan_dirs
from backend.download_service import DownloadService
from backend.llm_service import LLMService
from backend.npu_monitor import get_npu_monitor
from backend.system_status import get_memory_status, get_process_memory


FRONTEND_DIR = ROOT_DIR / "frontend"
DOWNLOAD_SCRIPT = ROOT_DIR / "app" / "core" / "download_script.py"
DEFAULT_SESSION_TITLE = "New Chat"

app = FastAPI(title="Idle NPU Waker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_lock = threading.Lock()
session_mgr = SessionManager()
llm_service = LLMService()
download_service = DownloadService(
    str(DOWNLOAD_SCRIPT), str(DOWNLOAD_CACHE_DIR), str(MODELS_DIR)
)
npu_monitor = get_npu_monitor()


class SessionCreateRequest(BaseModel):
    title: Optional[str] = None
    is_temporary: Optional[bool] = False


class SessionRenameRequest(BaseModel):
    title: str = Field(..., min_length=1)


class ModelLoadRequest(BaseModel):
    source: str = "local"
    model_id: str = ""
    path: str
    device: str = "AUTO"
    max_prompt_len: int = 16384


class ModelDeleteRequest(BaseModel):
    path: str = Field(..., min_length=1)


class FileAttachment(BaseModel):
    name: str = Field(..., min_length=1)
    content: str
    truncated: Optional[bool] = None


class ChatStreamRequest(BaseModel):
    session_id: str
    text: str
    config: Optional[Dict[str, Any]] = None
    attachments: Optional[List[FileAttachment]] = None


class ChatRegenerateRequest(BaseModel):
    session_id: str
    config: Optional[Dict[str, Any]] = None


class MessageEditRequest(BaseModel):
    index: int = Field(..., ge=0)
    content: str


class MessageRetryRequest(BaseModel):
    index: int = Field(..., ge=0)


class DownloadRequest(BaseModel):
    repo_id: str


def _sse(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sanitize_attachments(attachments: Optional[List[FileAttachment]]) -> List[Dict[str, Any]]:
    safe: List[Dict[str, Any]] = []
    if not attachments:
        return safe
    for item in attachments:
        data = item.model_dump() if isinstance(item, BaseModel) else dict(item)
        name = str(data.get("name", "")).strip()
        content = str(data.get("content", ""))
        if not name or not content:
            continue
        encoded = content.encode("utf-8", errors="ignore")
        truncated = len(encoded) > MAX_FILE_BYTES
        if truncated:
            content = encoded[:MAX_FILE_BYTES].decode("utf-8", errors="ignore")
        safe.append({"name": name[:200], "content": content, "truncated": truncated})
    return safe


def _format_attachments(attachments: List[Dict[str, Any]]) -> str:
    if not attachments:
        return ""
    lines = ["[Attachments]"]
    for item in attachments:
        name = str(item.get("name", ""))
        content = str(item.get("content", ""))
        if not content:
            continue
        lines.append(f"[File: {name}]")
        lines.append(content)
        lines.append("[/File]")
    return "\n".join(lines)


def _merge_message_attachments(message: Dict[str, Any]) -> Dict[str, Any]:
    content = message.get("content", "")
    attachments = message.get("attachments") or []
    if attachments:
        block = _format_attachments(attachments)
        if block:
            content = f"{content}\n\n{block}" if content else block
    return {"role": message.get("role", "user"), "content": content}


def _build_messages(history, config: Dict[str, Any]):
    sys_prompt = config.get("system_prompt", "")
    try:
        max_turns = int(config.get("max_history_turns", 10))
    except (TypeError, ValueError):
        max_turns = 10

    if max_turns > 0:
        sliced_history = history[-(max_turns * 2) :]
    else:
        sliced_history = history[-1:] if history else []

    messages = []
    if sys_prompt:
        messages.append({"role": "system", "content": sys_prompt})
    messages.extend(_merge_message_attachments(msg) for msg in sliced_history)
    return messages


@app.get("/api/health")
def api_health():
    return {"status": "ok"}


@app.get("/api/config")
def api_config():
    return {
        "app_version": APP_VERSION,
        "default_config": DEFAULT_CONFIG,
        "config_groups": CONFIG_GROUPS,
        "preset_models": PRESET_MODELS,
        "download_models": NPU_COLLECTION_MODELS,
        "download_collection_url": NPU_COLLECTION_URL,
        "model_specific_configs": MODEL_SPECIFIC_CONFIGS,
        "available_devices": AVAILABLE_DEVICES,
        "models_dir": str(MODELS_DIR),
        "max_file_bytes": MAX_FILE_BYTES,
    }


LANG_DIR = ROOT_DIR / "app" / "lang"
AVAILABLE_LANGS = ["en_US", "zh_CN"]
LANG_PREF_FILE = DATA_DIR / "lang.json"


def _load_saved_lang() -> str:
    if not LANG_PREF_FILE.exists():
        return "en_US"
    try:
        data = json.loads(LANG_PREF_FILE.read_text(encoding="utf-8"))
        lang = data.get("lang")
        return lang if lang in AVAILABLE_LANGS else "en_US"
    except (OSError, json.JSONDecodeError, AttributeError):
        return "en_US"


current_lang = _load_saved_lang()


class LangPreferenceRequest(BaseModel):
    lang: str = Field(..., min_length=1)


@app.get("/api/i18n")
def api_i18n_list():
    return {"languages": AVAILABLE_LANGS, "default": "en_US"}


@app.get("/api/i18n/{lang}")
def api_i18n(lang: str):
    if lang not in AVAILABLE_LANGS:
        raise HTTPException(status_code=404, detail="Language not found")
    lang_file = LANG_DIR / f"{lang}.json"
    if not lang_file.exists():
        raise HTTPException(status_code=404, detail="Language file not found")
    with open(lang_file, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/lang")
def api_get_lang():
    return {"lang": current_lang}


@app.post("/api/lang")
def api_set_lang(req: LangPreferenceRequest):
    lang = req.lang
    if lang not in AVAILABLE_LANGS:
        raise HTTPException(status_code=400, detail="Unsupported language")
    global current_lang
    current_lang = lang
    try:
        LANG_PREF_FILE.write_text(json.dumps({"lang": lang}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return {"lang": current_lang}


@app.get("/api/models/local")
def api_models_local():
    return {"models": scan_dirs([MODELS_DIR])}


@app.get("/api/models/config")
def api_models_config(path: str = Query(..., min_length=1)):
    supported_keys = resolve_supported_setting_keys(
        model_name=Path(path).name,
        model_path=path
    )
    return {
        "config": load_model_json_configs(path),
        "supported_keys": sorted(supported_keys)
    }


@app.post("/api/models/load")
def api_models_load(req: ModelLoadRequest):
    try:
        model_path, device = llm_service.load_model(
            req.source, req.model_id, req.path, req.device, req.max_prompt_len
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"path": model_path, "device": device}


@app.get("/api/models/status")
def api_models_status():
    return llm_service.get_status()


@app.post("/api/models/delete")
def api_models_delete(req: ModelDeleteRequest):
    target = Path(req.path).resolve()
    models_root = MODELS_DIR.resolve()
    try:
        target.relative_to(models_root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid model path")
    if target == models_root:
        raise HTTPException(status_code=400, detail="Refuse to delete models root")
    if not target.exists():
        return {"ok": True, "removed": False}
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Invalid model path")

    status = llm_service.get_status()
    loaded_path = status.get("path") if isinstance(status, dict) else ""
    if status.get("loaded") and loaded_path:
        if Path(str(loaded_path)).resolve() == target:
            try:
                llm_service.unload_model()
            except RuntimeError as exc:
                raise HTTPException(status_code=409, detail=str(exc))

    try:
        shutil.rmtree(target)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Delete failed: {exc}")

    return {"ok": True, "removed": True}


@app.get("/api/sessions")
def api_sessions():
    with session_lock:
        sessions = [
            {"id": sid, "title": data.get("title", ""), "is_temporary": data.get("is_temporary", False)}
            for sid, data in session_mgr.sessions.items()
        ]
        # Include temporary sessions
        for sid, data in session_mgr.temp_sessions.items():
            sessions.append({
                "id": sid,
                "title": data.get("title", ""),
                "is_temporary": True
            })
        return {
            "sessions": sessions,
            "current_session_id": session_mgr.current_session_id,
        }


@app.post("/api/sessions")
def api_sessions_create(req: SessionCreateRequest):
    title = req.title or DEFAULT_SESSION_TITLE
    is_temporary = req.is_temporary or False
    with session_lock:
        sid = session_mgr.create_session(title, is_temporary=is_temporary)
        return {"id": sid, "title": title, "is_temporary": is_temporary}


@app.post("/api/sessions/{sid}/select")
def api_sessions_select(sid: str):
    with session_lock:
        if sid not in session_mgr.sessions and sid not in session_mgr.temp_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        session_mgr.current_session_id = sid
        session_mgr._save_sessions()
    return {"ok": True}


@app.put("/api/sessions/{sid}")
def api_sessions_rename(sid: str, req: SessionRenameRequest):
    with session_lock:
        if sid not in session_mgr.sessions and sid not in session_mgr.temp_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        session_mgr.rename_session(sid, req.title)
    return {"ok": True}


@app.delete("/api/sessions/{sid}")
def api_sessions_delete(sid: str):
    with session_lock:
        if sid not in session_mgr.sessions and sid not in session_mgr.temp_sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        session_mgr.delete_session(sid)
        return {"ok": True, "current_session_id": session_mgr.current_session_id}


@app.get("/api/sessions/{sid}/messages")
def api_sessions_messages(sid: str):
    with session_lock:
        session = session_mgr.get_session(sid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"messages": session.get("history", [])}


@app.post("/api/sessions/{sid}/messages/edit")
def api_sessions_messages_edit(sid: str, req: MessageEditRequest):
    with session_lock:
        session = session_mgr.get_session(sid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        history = session.get("history", [])
        if req.index >= len(history):
            raise HTTPException(status_code=400, detail="Message index out of range")
        if history[req.index].get("role") != "user":
            raise HTTPException(status_code=400, detail="Only user messages can be edited")

        history[req.index]["content"] = req.content
        session["history"] = history[: req.index + 1]
        if req.index == 0:
            session_mgr.update_title(req.content, sid=sid)
        else:
            session_mgr._save_sessions()

    return {"ok": True}


@app.post("/api/sessions/{sid}/messages/retry")
def api_sessions_messages_retry(sid: str, req: MessageRetryRequest):
    with session_lock:
        session = session_mgr.get_session(sid)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        history = session.get("history", [])
        if req.index >= len(history):
            raise HTTPException(status_code=400, detail="Message index out of range")
        if history[req.index].get("role") != "assistant":
            raise HTTPException(status_code=400, detail="Only assistant messages can be retried")

        session["history"] = history[: req.index]
        session_mgr._save_sessions()

    return {"ok": True}


@app.post("/api/chat/stream")
def api_chat_stream(req: ChatStreamRequest):
    with session_lock:
        session = session_mgr.get_session(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if not session.get("history"):
            session_mgr.update_title(req.text, sid=req.session_id)

        attachments = _sanitize_attachments(req.attachments)
        msg_kwargs: Dict[str, Any] = {}
        if attachments:
            msg_kwargs["attachments"] = attachments
        session_mgr.add_message("user", req.text, sid=req.session_id, **msg_kwargs)
        session_mgr.current_session_id = req.session_id
        session_mgr._save_sessions()
        history = list(session.get("history", []))

    config = DEFAULT_CONFIG.copy()
    if req.config:
        config.update(req.config)

    messages = _build_messages(history, config)
    assistant_text = ""

    def event_stream():
        nonlocal assistant_text
        try:
            res_queue, done_event = llm_service.generate(messages, config)
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})
            return

        try:
            while True:
                try:
                    item = res_queue.get(timeout=0.1)
                except queue.Empty:
                    if done_event.is_set():
                        break
                    continue

                msg_type = item.get("type")
                if msg_type == "token":
                    token = item.get("token", "")
                    assistant_text += token
                    yield _sse({"type": "token", "token": token})
                elif msg_type == "error":
                    yield _sse({"type": "error", "message": item.get("msg", "Error")})
                    break
                elif msg_type == "done":
                    stats = item.get("stats", {})
                    yield _sse({"type": "done", "stats": stats})
                    break
        finally:
            llm_service.finish_generation()
            if assistant_text:
                with session_lock:
                    session_mgr.add_message("assistant", assistant_text, sid=req.session_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/api/chat/regenerate")
def api_chat_regenerate(req: ChatRegenerateRequest):
    with session_lock:
        session = session_mgr.get_session(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        history = list(session.get("history", []))

    if not history:
        raise HTTPException(status_code=400, detail="No messages to regenerate")
    if history[-1].get("role") != "user":
        raise HTTPException(status_code=400, detail="Last message must be a user message")

    config = DEFAULT_CONFIG.copy()
    if req.config:
        config.update(req.config)

    messages = _build_messages(history, config)
    assistant_text = ""

    def event_stream():
        nonlocal assistant_text
        try:
            res_queue, done_event = llm_service.generate(messages, config)
        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})
            return

        try:
            while True:
                try:
                    item = res_queue.get(timeout=0.1)
                except queue.Empty:
                    if done_event.is_set():
                        break
                    continue

                msg_type = item.get("type")
                if msg_type == "token":
                    token = item.get("token", "")
                    assistant_text += token
                    yield _sse({"type": "token", "token": token})
                elif msg_type == "error":
                    yield _sse({"type": "error", "message": item.get("msg", "Error")})
                    break
                elif msg_type == "done":
                    stats = item.get("stats", {})
                    yield _sse({"type": "done", "stats": stats})
                    break
        finally:
            llm_service.finish_generation()
            if assistant_text:
                with session_lock:
                    session_mgr.add_message("assistant", assistant_text, sid=req.session_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/api/chat/stop")
def api_chat_stop():
    llm_service.stop()
    return {"ok": True}


@app.post("/api/download/stream")
def api_download_stream(req: DownloadRequest):
    try:
        res_queue = download_service.start(req.repo_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    def event_stream():
        while True:
            item = res_queue.get()
            yield _sse(item)
            if item.get("type") == "done":
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/api/download/stop")
def api_download_stop():
    download_service.stop()
    return {"ok": True}


@app.get("/api/status")
def api_status():
    return {
        "memory": get_memory_status(),
        "app": get_process_memory(os.getpid()),
        "download": download_service.get_status(),
        "model": llm_service.get_status(),
    }


@app.post("/api/app/exit")
def api_app_exit():
    def _shutdown():
        try:
            llm_service.shutdown()
            download_service.stop()
            npu_monitor.stop()
        finally:
            time.sleep(0.2)
            os._exit(0)

    threading.Thread(target=_shutdown, daemon=True).start()
    return {"ok": True}


@app.post("/api/npu/start")
def api_npu_start():
    available = npu_monitor.start()
    return {"available": available, "searching": npu_monitor.is_searching()}


@app.get("/api/npu/status")
def api_npu_status():
    return {
        "available": npu_monitor.is_available(),
        "searching": npu_monitor.is_searching(),
        "current": npu_monitor.get_current(),
        "history": npu_monitor.get_history()
    }


@app.post("/api/npu/stop")
def api_npu_stop():
    npu_monitor.stop()
    return {"ok": True}


@app.get("/")
def index():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not built")
    return FileResponse(index_path, headers={"Cache-Control": "no-store"})


@app.get("/tray")
@app.get("/tray.html")
def tray_menu():
    tray_path = FRONTEND_DIR / "tray.html"
    if not tray_path.exists():
        raise HTTPException(status_code=404, detail="Tray menu not built")
    return FileResponse(tray_path, headers={"Cache-Control": "no-store"})


@app.get("/tray.css")
def tray_menu_css():
    css_path = FRONTEND_DIR / "tray.css"
    if not css_path.exists():
        raise HTTPException(status_code=404, detail="Tray stylesheet not built")
    return FileResponse(css_path, headers={"Cache-Control": "no-store"})


@app.get("/tray.js")
def tray_menu_js():
    js_path = FRONTEND_DIR / "tray.js"
    if not js_path.exists():
        raise HTTPException(status_code=404, detail="Tray script not built")
    return FileResponse(js_path, headers={"Cache-Control": "no-store"})

class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "no-store"
        return response


app.mount("/static", NoCacheStaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("shutdown")
def on_shutdown():
    llm_service.shutdown()
    download_service.stop()
    npu_monitor.stop()
