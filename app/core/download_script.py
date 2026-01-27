import sys
import shutil
import re
import threading
import inspect
from typing import Optional, Callable, Dict, Any, Set, Tuple, List
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

PATTERN_ANSI = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

_PRINT_LOCK = threading.Lock()

_EVENT_SINK: Optional[object] = None
_PROGRESS_AGGREGATOR = None


def _emit_legacy(event: Dict[str, Any]) -> None:
    event_type = event.get("type")
    if event_type == "progress":
        filename = event.get("file", "")
        percent = event.get("percent", 0)
        with _PRINT_LOCK:
            print(f"@PROGRESS@{filename}@{percent}", flush=True)
        return
    if event_type == "log":
        message = event.get("message", "")
        if message:
            with _PRINT_LOCK:
                print(f"@LOG@{message}", flush=True)
        return
    if event_type == "finished":
        path = event.get("path", "")
        if path:
            with _PRINT_LOCK:
                print(f"@FINISHED@{path}", flush=True)
        return
    if event_type == "error":
        message = event.get("message", "")
        if message:
            with _PRINT_LOCK:
                print(f"@ERROR@{message}", flush=True)
        return


def _emit_event(event: Dict[str, Any], sink: Optional[object] = None) -> None:
    target = sink if sink is not None else _EVENT_SINK
    if target is None:
        _emit_legacy(event)
        return
    try:
        if hasattr(target, "put"):
            target.put(event)
        else:
            target(event)
    except Exception:
        pass


class ProgressAggregator:
    def __init__(self, emit: Callable[[Dict[str, Any]], None], total_bytes: int = 0, total_files: int = 0):
        self._emit = emit
        self._lock = threading.Lock()
        self._total_bytes = max(0, int(total_bytes or 0))
        self._total_files = max(0, int(total_files or 0))
        self._downloaded_bytes = 0
        self._file_sizes: Dict[str, int] = {}
        self._file_downloaded: Dict[str, int] = {}
        self._finished_files: Set[str] = set()
        self._last_percent = -1

    def register_file(self, filename: str, file_size: int) -> None:
        if not filename:
            return
        size = max(0, int(file_size or 0))
        with self._lock:
            if filename not in self._file_sizes:
                self._file_sizes[filename] = size
                self._file_downloaded.setdefault(filename, 0)
                if self._total_bytes <= 0 and size > 0:
                    self._total_bytes += size

    def _compute_percent(self, filename: str) -> int:
        if self._total_bytes > 0:
            percent = int(self._downloaded_bytes * 100 / self._total_bytes)
        elif self._total_files > 0:
            completed = len(self._finished_files)
            file_progress = 0.0
            size = self._file_sizes.get(filename, 0)
            if size > 0:
                file_progress = self._file_downloaded.get(filename, 0) / size
            percent = int((completed + file_progress) * 100 / self._total_files)
        else:
            size = self._file_sizes.get(filename, 0)
            if size > 0:
                percent = int(self._file_downloaded.get(filename, 0) * 100 / size)
            else:
                percent = 0
        if percent < 0:
            percent = 0
        if percent > 100:
            percent = 100
        if percent < self._last_percent:
            percent = self._last_percent
        return percent

    def _emit_progress(self, filename: str) -> None:
        percent = self._compute_percent(filename)
        if percent == self._last_percent:
            return
        self._last_percent = percent
        self._emit({"type": "progress", "file": filename, "percent": percent})

    def update(self, filename: str, size: int) -> None:
        if not filename:
            return
        delta = int(size or 0)
        if delta <= 0:
            return
        with self._lock:
            current = self._file_downloaded.get(filename, 0)
            file_size = self._file_sizes.get(filename, 0)
            new_value = current + delta
            if file_size > 0 and new_value > file_size:
                new_value = file_size
            applied = new_value - current
            if applied <= 0:
                return
            self._file_downloaded[filename] = new_value
            self._downloaded_bytes += applied
            self._emit_progress(filename)

    def end(self, filename: str) -> None:
        if not filename:
            return
        with self._lock:
            self._finished_files.add(filename)
            file_size = self._file_sizes.get(filename, 0)
            current = self._file_downloaded.get(filename, 0)
            if file_size > 0 and current < file_size:
                self._downloaded_bytes += file_size - current
                self._file_downloaded[filename] = file_size
            self._emit_progress(filename)


class DownloadProgressCallback:
    def __init__(self, filename: str, file_size: int):
        self.filename = filename
        self.file_size = file_size or 0
        if _PROGRESS_AGGREGATOR is not None:
            _PROGRESS_AGGREGATOR.register_file(filename, self.file_size)

    def update(self, size: int):
        if _PROGRESS_AGGREGATOR is not None:
            _PROGRESS_AGGREGATOR.update(self.filename, size)

    def end(self):
        if _PROGRESS_AGGREGATOR is not None:
            _PROGRESS_AGGREGATOR.end(self.filename)


class StreamAdapter:
    def __init__(self, emit: Callable[[Dict[str, Any]], None]):
        self._emit = emit

    def write(self, text):
        if not text:
            return

        clean_text = PATTERN_ANSI.sub('', text).strip()
        if clean_text and not clean_text.startswith("%") and "Downloading" not in clean_text:
            self._emit({"type": "log", "message": clean_text})

    def flush(self):
        sys.stdout.flush()

def _compute_download_plan(repo_id: str, cache_dir: Optional[str]) -> Tuple[int, int]:
    from modelscope.hub.api import HubApi, ModelScopeConfig
    from modelscope.hub.snapshot_download import create_temporary_directory_and_cache
    from modelscope.utils.constant import REPO_TYPE_MODEL, DEFAULT_MODEL_REVISION
    import uuid

    api = HubApi()
    endpoint = api.get_endpoint_for_read(repo_id=repo_id, repo_type=REPO_TYPE_MODEL)
    cookies = ModelScopeConfig.get_cookies()
    revision_detail = api.get_valid_revision_detail(
        repo_id, revision=DEFAULT_MODEL_REVISION, cookies=cookies, endpoint=endpoint
    )
    revision = revision_detail["Revision"]
    headers = {
        "user-agent": ModelScopeConfig.get_user_agent(user_agent=None),
        "snapshot-identifier": str(uuid.uuid4().hex),
        "Snapshot": "True",
    }
    _, cache = create_temporary_directory_and_cache(
        repo_id, cache_dir=cache_dir, repo_type=REPO_TYPE_MODEL
    )
    if cache.cached_model_revision is not None:
        headers["cached_model_revision"] = cache.cached_model_revision

    repo_files = api.get_model_files(
        model_id=repo_id,
        revision=revision,
        recursive=True,
        use_cookies=False if cookies is None else cookies,
        headers=headers,
        endpoint=endpoint,
    )

    total_bytes = 0
    total_files = 0
    for repo_file in repo_files:
        if repo_file.get("Type") == "tree":
            continue
        cache_key = {
            "Path": repo_file.get("Path"),
            "Revision": repo_file.get("Revision"),
        }
        if cache.exists(cache_key):
            continue
        size = repo_file.get("Size") or 0
        if isinstance(size, str):
            try:
                size = int(size)
            except ValueError:
                size = 0
        if size < 0:
            size = 0
        total_bytes += size
        total_files += 1
    return total_bytes, total_files


def _candidate_model_names(repo_id: str) -> List[str]:
    name = repo_id.split("/")[-1].strip()
    if not name:
        return []
    names = [name]
    replaced = name.replace(".", "___")
    if replaced != name:
        names.append(replaced)
    return names


def _find_existing_model(target_root: str, repo_id: str) -> Optional[str]:
    root = Path(target_root)
    for name in _candidate_model_names(repo_id):
        if (root / name).exists():
            return name
    return None


def run_download_task(args, event_sink: Optional[object] = None):
    global _EVENT_SINK, _PROGRESS_AGGREGATOR
    _EVENT_SINK = event_sink

    def emit(event: Dict[str, Any]) -> None:
        _emit_event(event, event_sink)

    def emit_log(message: str) -> None:
        if message:
            emit({"type": "log", "message": message})

    def emit_error(message: str) -> None:
        if message:
            emit({"type": "error", "message": message})

    def emit_finished(path: str) -> None:
        if path:
            emit({"type": "finished", "path": path})

    def finalize() -> None:
        if event_sink is not None:
            emit({"type": "done"})
        _EVENT_SINK = None
        _PROGRESS_AGGREGATOR = None

    if len(args) < 3:
        emit_error("参数不足")
        finalize()
        return

    repo_id = args[0]
    cache_dir = args[1]
    target_root = args[2]
    existing = _find_existing_model(target_root, repo_id)
    if existing:
        emit_error(f"模型已存在: {existing}")
        finalize()
        return

    try:
        from modelscope import snapshot_download
    except ImportError:
        emit_error("未安装 modelscope")
        finalize()
        return

    sys.stderr = StreamAdapter(emit)
    emit_log(f"正在启动下载进程...")
    emit_log(f"目标模型: {repo_id}")

    try:
        total_bytes = 0
        total_files = 0
        try:
            total_bytes, total_files = _compute_download_plan(repo_id, cache_dir)
        except Exception:
            total_bytes = 0
            total_files = 0
        _PROGRESS_AGGREGATOR = ProgressAggregator(emit, total_bytes, total_files)
        progress_callbacks = [DownloadProgressCallback]
        if "progress_callbacks" in inspect.signature(snapshot_download).parameters:
            temp_path = snapshot_download(
                repo_id,
                cache_dir=cache_dir,
                progress_callbacks=progress_callbacks,
            )
        else:
            temp_path = snapshot_download(repo_id, cache_dir=cache_dir)
        temp_path_obj = Path(temp_path)
        emit_log("下载完成，正在整理文件...")
        model_name = temp_path_obj.name
        final_path = Path(target_root) / model_name
        if final_path.exists():
            emit_log(f"覆盖旧模型: {model_name}")
            shutil.rmtree(final_path)
        shutil.move(str(temp_path_obj), str(final_path))
        emit_finished(str(final_path))
    except Exception as e:
        emit_error(f"{str(e)}")
    finally:
        finalize()

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        run_download_task(sys.argv[1:])
