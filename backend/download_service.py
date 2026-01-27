import multiprocessing
import queue
import threading
import time
from pathlib import Path
from typing import Optional, Dict, List


def _run_download_task(args: List[str], event_queue) -> None:
    try:
        from app.core.download_script import run_download_task
        run_download_task(args, event_queue)
    except Exception as exc:
        try:
            event_queue.put({"type": "error", "message": str(exc)})
        except Exception:
            pass
        try:
            event_queue.put({"type": "done"})
        except Exception:
            pass


class DownloadService:
    def __init__(self, script_path: str, cache_dir: str, models_dir: str) -> None:
        self._script_path = script_path
        self._cache_dir = cache_dir
        self._models_dir = models_dir

        self._lock = threading.Lock()
        self._process: Optional[multiprocessing.Process] = None
        self._ipc_queue: Optional[object] = None
        self._queue: Optional[queue.Queue] = None
        self._reader: Optional[threading.Thread] = None
        self._running = False
        self._status: Dict[str, object] = {
            "running": False,
            "repo_id": "",
            "percent": 0,
            "file": "",
            "message": "",
            "error": "",
            "path": "",
            "started_at": None,
            "updated_at": None,
        }

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def get_status(self) -> Dict[str, object]:
        with self._lock:
            return dict(self._status)

    def _update_status(self, **kwargs) -> None:
        now = time.time()
        with self._lock:
            self._status.update(kwargs)
            self._status["updated_at"] = now

    def start(self, repo_id: str) -> queue.Queue:
        with self._lock:
            if self._running:
                raise RuntimeError("Download already running")
            model_name = repo_id.split("/")[-1].strip()
            if model_name:
                candidates = [model_name]
                replaced = model_name.replace(".", "___")
                if replaced != model_name:
                    candidates.append(replaced)
                models_root = Path(self._models_dir)
                for name in candidates:
                    if (models_root / name).exists():
                        raise RuntimeError(f"模型已存在: {name}")

            ctx = multiprocessing.get_context("spawn")
            self._ipc_queue = ctx.Queue()
            self._queue = queue.Queue()
            self._process = ctx.Process(
                target=_run_download_task,
                args=([repo_id, self._cache_dir, self._models_dir], self._ipc_queue),
                daemon=True,
            )
            self._process.start()
            self._running = True
            self._reader = threading.Thread(target=self._read_loop, daemon=True)
            self._reader.start()
            self._status = {
                "running": True,
                "repo_id": repo_id,
                "percent": 0,
                "file": "",
                "message": "",
                "error": "",
                "path": "",
                "started_at": time.time(),
                "updated_at": time.time(),
            }

            return self._queue

    def stop(self) -> None:
        with self._lock:
            process = self._process
            ipc_queue = self._ipc_queue
            if not process:
                return
            try:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=1)
            finally:
                self._running = False
                self._status["running"] = False
                self._status["message"] = "cancelled"
                self._status["updated_at"] = time.time()

        if ipc_queue is not None:
            try:
                ipc_queue.put({"type": "cancelled"})
            except Exception:
                pass
            try:
                ipc_queue.put({"type": "done"})
            except Exception:
                pass

    def _handle_event(self, item: Dict[str, object]) -> None:
        event_type = item.get("type")
        if event_type == "progress":
            percent = int(item.get("percent") or 0)
            file_name = item.get("file") or ""
            self._update_status(percent=percent, file=file_name, message="")
            return
        if event_type == "finished":
            path = item.get("path") or ""
            self._update_status(path=path)
            return
        if event_type == "error":
            message = item.get("message") or ""
            self._update_status(error=message, message="")
            return
        if event_type == "cancelled":
            self._update_status(message="cancelled")
            return
        if event_type == "log":
            message = item.get("message") or ""
            if message:
                self._update_status(message=message)

    def _read_loop(self) -> None:
        assert self._ipc_queue is not None
        assert self._queue is not None

        done = False
        while True:
            try:
                item = self._ipc_queue.get(timeout=0.2)
            except queue.Empty:
                if self._process is not None and not self._process.is_alive():
                    break
                continue

            if not isinstance(item, dict):
                continue
            self._handle_event(item)
            self._queue.put(item)
            if item.get("type") == "done":
                done = True
                break

        if not done:
            exit_code = None
            if self._process is not None:
                self._process.join(timeout=0)
                exit_code = self._process.exitcode
            if exit_code not in (0, None):
                error = f"Download exited with code {exit_code}"
                self._update_status(error=error, message="")
                self._queue.put({"type": "error", "message": error})
            self._queue.put({"type": "done"})

        with self._lock:
            self._running = False
            self._status["running"] = False
            self._status["updated_at"] = time.time()
