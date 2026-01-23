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

def main() -> None:
    sys.stdout = _ensure_stream(sys.stdout, "__stdout__")
    sys.stderr = _ensure_stream(sys.stderr, "__stderr__")
    from backend.server import main as run_server

    run_server()


if __name__ == "__main__":
    main()
