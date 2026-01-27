import json
from pathlib import Path
from typing import Iterable

VLM_MARKERS = [
    "openvino_vision_embeddings_model.xml",
    "openvino_vision_model.xml",
    "openvino_image_embeddings_model.xml",
]
LANGUAGE_MARKER = "openvino_language_model.xml"
LLM_MARKERS = ["openvino_model.xml", LANGUAGE_MARKER]
IMAGE_DIR_MARKERS = [
    "scheduler",
    "text_encoder",
    "text_encoder_2",
    "tokenizer",
    "tokenizer_2",
    "transformer",
    "vae_decoder",
    "vae_encoder",
]
IMAGE_TASKS = {"text-to-image", "text_to_image", "text2image", "image-generation", "image_generation", "txt2img"}


def _has_any(root: Path, names: Iterable[str]) -> bool:
    for name in names:
        if any(root.rglob(name)):
            return True
    return False

def _is_image_model(root: Path) -> bool:
    config_path = root / "configuration.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            task = str(data.get("task", "")).strip().lower()
            if task in IMAGE_TASKS:
                return True
        except Exception:
            pass

    index_path = root / "model_index.json"
    if index_path.exists():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
            class_name = str(data.get("_class_name", "")).lower()
            if "pipeline" in class_name or "diffusion" in class_name or "flux" in class_name:
                return True
        except Exception:
            return True
        return True

    for name in IMAGE_DIR_MARKERS:
        if (root / name).exists():
            return True
    return False


def detect_model_kind(model_path: Path) -> str:
    try:
        root = Path(model_path)
    except Exception:
        return "llm"
    if not root.exists():
        return "llm"
    if _is_image_model(root):
        return "image"
    has_language = _has_any(root, [LANGUAGE_MARKER])
    has_vision = _has_any(root, VLM_MARKERS)
    if has_language and has_vision:
        return "vlm"
    if _has_any(root, LLM_MARKERS):
        return "llm"
    return "llm"
