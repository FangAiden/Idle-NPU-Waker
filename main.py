import multiprocessing
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def _ensure_stream(stream, fallback_label: str):
    if stream is not None and hasattr(stream, "isatty"):
        return stream
    preferred = getattr(sys, fallback_label, None)
    if preferred is not None and hasattr(preferred, "isatty"):
        return preferred
    return open(os.devnull, "w", encoding="utf-8")

def _ensure_pipe_stream(stream, fallback_fd: int):
    if stream is not None and hasattr(stream, "write"):
        return stream
    try:
        return open(fallback_fd, "w", encoding="utf-8", closefd=False)
    except OSError:
        return open(os.devnull, "w", encoding="utf-8")


def _run_download_mode(argv: list[str]) -> None:
    sys.stdout = _ensure_pipe_stream(sys.stdout, 1)
    sys.stderr = _ensure_pipe_stream(sys.stderr, 2)
    from app.core.download_script import run_download_task

    args = [arg for arg in argv if arg != "--download-script"]
    run_download_task(args)


def main() -> None:
    multiprocessing.freeze_support()
    if "--download-script" in sys.argv:
        _run_download_mode(sys.argv[1:])
        return
    sys.stdout = _ensure_stream(sys.stdout, "__stdout__")
    sys.stderr = _ensure_stream(sys.stderr, "__stderr__")
    from backend.server import main as run_server

    run_server()


if __name__ == "__main__":
    main()
