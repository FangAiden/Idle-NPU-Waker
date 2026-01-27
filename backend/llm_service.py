import multiprocessing
import queue
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from app.core.llm_process import llm_process_entry
from app.config import LOGS_DIR
from backend.system_status import get_process_memory

_LOG_PATH = Path(LOGS_DIR) / "backend.log"

def _log(msg: str) -> None:
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{ts}][pid {multiprocessing.current_process().pid}] {msg}\n")
    except Exception:
        pass


class LLMService:
    def __init__(self) -> None:
        self._ctx = multiprocessing.get_context("spawn")
        self._cmd_queue = self._ctx.Queue()
        self._res_queue = self._ctx.Queue()
        self._stop_event = self._ctx.Event()

        self._process = None
        self._monitor_thread = None

        self._lock = threading.Lock()
        self._load_event = threading.Event()
        self._load_result: Optional[Dict[str, object]] = None
        self._loading = False
        self._load_stage = ""
        self._load_message = ""
        self._load_started_at: Optional[float] = None

        self._active_generation = False
        self._generation_queue: Optional[queue.Queue] = None
        self._generation_done = threading.Event()

        self._model_loaded = False
        self._model_path: Optional[str] = None
        self._device: Optional[str] = None
        self._model_kind: Optional[str] = None

    def _start_process_if_needed(self) -> None:
        if self._process is None or not self._process.is_alive():
            _log("Spawning model process")
            self._process = self._ctx.Process(
                target=llm_process_entry,
                args=(self._cmd_queue, self._res_queue, self._stop_event),
                daemon=True,
            )
            self._process.start()
            _log(f"Model process started pid={self._process.pid}")
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()

    def _monitor_loop(self) -> None:
        while True:
            try:
                msg = self._res_queue.get()
            except (EOFError, BrokenPipeError):
                break
            except Exception:
                continue

            msg_type = msg.get("type")

            if msg_type == "loaded":
                _log("Load complete")
                with self._lock:
                    self._device = msg.get("dev")
                    self._model_kind = msg.get("kind") or self._model_kind
                    self._load_result = {"ok": True, "dev": self._device or "AUTO"}
                    self._loading = False
                    self._load_stage = "ready"
                    self._load_message = ""
                    self._load_event.set()
                continue

            if msg_type == "load_stage":
                _log(f"Load stage: {msg.get('stage')} msg={msg.get('message')}")
                with self._lock:
                    self._loading = True
                    self._load_stage = msg.get("stage", "") or ""
                    self._load_message = msg.get("message", "") or ""
                continue

            if msg_type == "token":
                if self._generation_queue is not None:
                    self._generation_queue.put({"type": "token", "token": msg.get("token", "")})
                continue

            if msg_type == "image":
                if self._generation_queue is not None:
                    self._generation_queue.put({"type": "image", "attachments": msg.get("attachments") or []})
                continue

            if msg_type == "finished":
                if self._generation_queue is not None:
                    stats = msg.get("stats", {})
                    self._generation_queue.put({"type": "done", "stats": stats})
                    self._generation_done.set()
                continue

            if msg_type == "error":
                if self._generation_queue is not None:
                    self._generation_queue.put({"type": "error", "msg": msg.get("msg", "Unknown error")})
                    self._generation_done.set()
                else:
                    _log(f"Load error: {msg.get('msg')}")
                    with self._lock:
                        self._load_result = {"ok": False, "error": msg.get("msg", "Unknown error")}
                        self._loading = False
                        self._load_stage = "error"
                        self._load_message = msg.get("msg", "Unknown error")
                        self._load_event.set()

    def load_model(
        self, source: str, model_id: str, model_dir: str, device: str, max_prompt_len: int = 16384
    ) -> Tuple[str, str, str]:
        with self._lock:
            if self._active_generation:
                raise RuntimeError("Generation in progress")

            self._start_process_if_needed()
            self._load_event.clear()
            self._load_result = None
            self._model_path = model_dir
            self._loading = True
            self._load_stage = "start"
            self._load_message = ""
            self._load_started_at = time.time()

            _log(f"Load request path={model_dir} device={device} source={source}")
            self._cmd_queue.put(
                {"type": "load", "args": (source, model_id, model_dir, device, max_prompt_len)}
            )

        deadline = time.time() + 300
        while True:
            if self._load_event.wait(timeout=0.5):
                break
            if time.time() >= deadline:
                _log("Model load timed out")
                with self._lock:
                    self._load_result = {"ok": False, "error": "Model load timed out"}
                    self._loading = False
                    self._load_stage = "error"
                    self._load_message = "Model load timed out"
                    self._load_event.set()
                if self._process is not None and self._process.is_alive():
                    try:
                        self._process.terminate()
                        self._process.join(timeout=1)
                    except Exception:
                        pass
                break
            if self._process is not None and not self._process.is_alive():
                _log("Model process exited during load")
                with self._lock:
                    self._load_result = {"ok": False, "error": "Model process exited"}
                    self._loading = False
                    self._load_stage = "error"
                    self._load_message = "Model process exited"
                    self._load_event.set()
                break

        if not self._load_result or not self._load_result.get("ok"):
            error_msg = "Model load failed"
            if self._load_result and self._load_result.get("error"):
                error_msg = self._load_result["error"]
            raise RuntimeError(error_msg)

        self._model_loaded = True
        return (self._model_path or "", self._device or "AUTO", self._model_kind or "llm")

    def get_status(self) -> Dict[str, object]:
        with self._lock:
            process_alive = self._process is not None and self._process.is_alive()
            loaded = bool(self._model_loaded and process_alive)
            pid = self._process.pid if process_alive and self._process else None
            path = self._model_path or ""
            device = self._device or "AUTO"
            kind = self._model_kind or "llm"
            loading = self._loading
            load_stage = self._load_stage
            load_message = self._load_message
            load_started_at = self._load_started_at
        memory = get_process_memory(pid) if loaded else {"rss": 0, "private": 0}
        return {
            "loaded": loaded,
            "path": path,
            "device": device,
            "kind": kind,
            "pid": pid or 0,
            "memory": memory,
            "loading": loading,
            "load_stage": load_stage,
            "load_message": load_message,
            "load_started_at": load_started_at or 0,
        }

    def generate(self, messages, config):
        with self._lock:
            if not self._model_loaded:
                raise RuntimeError("Model not loaded")
            if self._active_generation:
                raise RuntimeError("Generation already running")

            self._start_process_if_needed()
            self._active_generation = True
            self._generation_queue = queue.Queue()
            self._generation_done.clear()

            self._cmd_queue.put(
                {"type": "generate", "messages": messages, "config": config}
            )

        return self._generation_queue, self._generation_done

    def finish_generation(self) -> None:
        with self._lock:
            self._active_generation = False
            self._generation_queue = None
            self._generation_done.clear()

    def stop(self) -> None:
        self._stop_event.set()

    def unload_model(self) -> None:
        with self._lock:
            if self._active_generation:
                raise RuntimeError("Generation in progress")
            self._active_generation = False
            self._generation_queue = None
            self._generation_done.clear()
            self._model_loaded = False
            self._model_path = None
            self._device = None
            self._model_kind = None
            self._loading = False
            self._load_stage = ""
            self._load_message = ""
            self._load_started_at = None

        if self._process and self._process.is_alive():
            try:
                self._cmd_queue.put(None)
                self._process.join(timeout=1)
            finally:
                if self._process.is_alive():
                    self._process.terminate()
                    self._process.join(timeout=1)
        self._process = None
        self._stop_event.set()

    def shutdown(self) -> None:
        with self._lock:
            self._active_generation = False
            self._generation_queue = None
            self._generation_done.clear()

        if self._process:
            try:
                self._cmd_queue.put(None)
                self._process.join(timeout=1)
            finally:
                if self._process.is_alive():
                    self._process.terminate()
