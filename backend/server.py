import os
import sys
from pathlib import Path

import uvicorn
import uvicorn.logging

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
# Avoid shadowing the top-level "app" package with backend/app.py.
sys.path = [p for p in sys.path if str(Path(p).resolve()) != str(BACKEND_DIR)]


def _ensure_stream(stream, fallback_label: str):
    if stream is not None and hasattr(stream, "isatty"):
        return stream
    preferred = getattr(sys, fallback_label, None)
    if preferred is not None and hasattr(preferred, "isatty"):
        return preferred
    return open(os.devnull, "w", encoding="utf-8")


sys.stdout = _ensure_stream(sys.stdout, "__stdout__")
sys.stderr = _ensure_stream(sys.stderr, "__stderr__")
if uvicorn.logging.sys.stdout is None:
    uvicorn.logging.sys.stdout = sys.stdout
if uvicorn.logging.sys.stderr is None:
    uvicorn.logging.sys.stderr = sys.stderr


def main():
    host = os.environ.get("IDLE_NPU_HOST", "127.0.0.1")
    port = int(os.environ.get("IDLE_NPU_PORT", "8000"))
    from backend.app import app

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,
        use_colors=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
