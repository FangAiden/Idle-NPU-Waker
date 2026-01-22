import queue
import subprocess
import sys
import threading
import time
from typing import Optional, Dict


class DownloadService:
    def __init__(self, script_path: str, cache_dir: str, models_dir: str) -> None:
        self._script_path = script_path
        self._cache_dir = cache_dir
        self._models_dir = models_dir

        self._lock = threading.Lock()
        self._process: Optional[subprocess.Popen] = None
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

            cmd = [
                sys.executable,
                self._script_path,
                repo_id,
                self._cache_dir,
                self._models_dir,
            ]
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
                bufsize=1,
            )
            self._queue = queue.Queue()
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
            if not self._process:
                return
            try:
                self._process.kill()
            finally:
                self._running = False
                self._status["running"] = False
                self._status["message"] = "cancelled"
                self._status["updated_at"] = time.time()

    def _read_loop(self) -> None:
        assert self._process is not None
        assert self._queue is not None
        assert self._process.stdout is not None

        for raw in self._process.stdout:
            line = raw.strip()
            if not line:
                continue

            if line.startswith("@PROGRESS@"):
                parts = line.split("@")
                if len(parts) >= 4:
                    try:
                        percent = int(parts[3])
                    except ValueError:
                        percent = 0
                    self._update_status(percent=percent, file=parts[2], message="")
                    self._queue.put(
                        {"type": "progress", "file": parts[2], "percent": percent}
                    )
                continue

            if line.startswith("@FINISHED@"):
                parts = line.split("@")
                if len(parts) >= 3:
                    self._update_status(path=parts[2])
                    self._queue.put({"type": "finished", "path": parts[2]})
                continue

            if line.startswith("@ERROR@"):
                parts = line.split("@")
                if len(parts) >= 3:
                    self._update_status(error=parts[2], message="")
                    self._queue.put({"type": "error", "message": parts[2]})
                continue

            if line.startswith("@LOG@"):
                content = line[5:].strip()
                if content:
                    self._update_status(message=content)
                    self._queue.put({"type": "log", "message": content})
                continue

            self._update_status(message=line)
            self._queue.put({"type": "log", "message": line})

        exit_code = self._process.wait()
        if exit_code != 0:
            self._update_status(error=f"Download exited with code {exit_code}")
            self._queue.put(
                {"type": "error", "message": f"Download exited with code {exit_code}"}
            )
        self._queue.put({"type": "done"})

        with self._lock:
            self._running = False
            self._status["running"] = False
            self._status["updated_at"] = time.time()
