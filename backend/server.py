import os
import sys
from pathlib import Path

import uvicorn

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
# Avoid shadowing the top-level "app" package with backend/app.py.
sys.path = [p for p in sys.path if str(Path(p).resolve()) != str(BACKEND_DIR)]


def main():
    host = os.environ.get("IDLE_NPU_HOST", "127.0.0.1")
    port = int(os.environ.get("IDLE_NPU_PORT", "8000"))
    from backend.app import app

    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
