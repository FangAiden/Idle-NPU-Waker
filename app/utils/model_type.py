from pathlib import Path
from typing import Iterable

VLM_MARKERS = [
    "openvino_vision_embeddings_model.xml",
    "openvino_vision_model.xml",
    "openvino_image_embeddings_model.xml",
]
LANGUAGE_MARKER = "openvino_language_model.xml"
LLM_MARKERS = ["openvino_model.xml", LANGUAGE_MARKER]


def _has_any(root: Path, names: Iterable[str]) -> bool:
    for name in names:
        if any(root.rglob(name)):
            return True
    return False


def detect_model_kind(model_path: Path) -> str:
    try:
        root = Path(model_path)
    except Exception:
        return "llm"
    if not root.exists():
        return "llm"
    has_language = _has_any(root, [LANGUAGE_MARKER])
    has_vision = _has_any(root, VLM_MARKERS)
    if has_language and has_vision:
        return "vlm"
    if _has_any(root, LLM_MARKERS):
        return "llm"
    return "llm"
