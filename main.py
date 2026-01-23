import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def main() -> None:
    from backend.server import main as run_server

    run_server()


if __name__ == "__main__":
    main()
