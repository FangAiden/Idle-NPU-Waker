import json
import os
import sys
from pathlib import Path

APP_VERSION = "1.0.1"
MAX_FILE_BYTES = 512 * 1024
MAX_IMAGE_BYTES = 5 * 1024 * 1024

if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).parent.resolve()
else:
    APP_ROOT = Path(__file__).parent.parent.resolve()

env_data_dir = os.environ.get("IDLE_NPU_DATA_DIR")
if env_data_dir:
    DATA_DIR = Path(env_data_dir).expanduser().resolve()
elif getattr(sys, "frozen", False):
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            DATA_DIR = Path(base) / "IdleNPUWaker"
        else:
            DATA_DIR = Path.home() / "AppData" / "Local" / "IdleNPUWaker"
    elif sys.platform == "darwin":
        DATA_DIR = Path.home() / "Library" / "Application Support" / "IdleNPUWaker"
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        DATA_DIR = Path(xdg) / "IdleNPUWaker" if xdg else Path.home() / ".local" / "share" / "IdleNPUWaker"
else:
    DATA_DIR = APP_ROOT

PATHS_CONFIG_FILE = DATA_DIR / "paths.json"

def _load_path_overrides(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _resolve_path(value: str, default: Path) -> Path:
    if not value:
        return default
    try:
        return Path(value).expanduser().resolve()
    except Exception:
        return default

_PATH_OVERRIDES = _load_path_overrides(PATHS_CONFIG_FILE)

CONFIG_DIR = _resolve_path(_PATH_OVERRIDES.get("config_dir"), DATA_DIR / "config")
LOGS_DIR = _resolve_path(_PATH_OVERRIDES.get("logs_dir"), DATA_DIR)
MODELS_DIR = _resolve_path(_PATH_OVERRIDES.get("models_dir"), DATA_DIR / "models")
DOWNLOAD_CACHE_DIR = _resolve_path(_PATH_OVERRIDES.get("download_cache_dir"), DATA_DIR / ".download_temp")
OV_CACHE_DIR = _resolve_path(_PATH_OVERRIDES.get("ov_cache_dir"), DATA_DIR / ".ov_cache")
SESSIONS_DB_PATH = _resolve_path(_PATH_OVERRIDES.get("sessions_db"), DATA_DIR / "sessions.db")

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
OV_CACHE_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_path_overrides() -> dict:
    return dict(_PATH_OVERRIDES)

def save_path_overrides(overrides: dict) -> None:
    PATHS_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    sanitized = {k: str(v) for k, v in overrides.items() if v}
    PATHS_CONFIG_FILE.write_text(json.dumps(sanitized, ensure_ascii=False, indent=2), encoding="utf-8")

DEFAULT_CONFIG = {
    "max_new_tokens": 1024,
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "repetition_penalty": 1.1,
    "do_sample": True,
    "system_prompt": "You are a helpful AI assistant.",
    "max_history_turns": 10,
    "add_generation_prompt": True,
    "enable_thinking": True,
    "skip_special_tokens": True,
    "negative_prompt": "",
    "width": 1024,
    "height": 1024,
    "num_inference_steps": 4,
    "guidance_scale": 0.0,
    "num_images_per_prompt": 1,
    "rng_seed": -1
}

CONFIG_GROUPS = [
    {
        "title_key": "grp_generation",
        "options": {
            "max_new_tokens": {
                "type": "int", "min": 128, "max": 8192, "step": 128, "default": 1024,
                "label_key": "conf_max_tokens", "widget": "slider"
            },
            "temperature": {
                "type": "float", "min": 0.0, "max": 2.0, "step": 0.1, "default": 0.7,
                "label_key": "conf_temp", "widget": "slider"
            },
            "top_p": {
                "type": "float", "min": 0.0, "max": 1.0, "step": 0.05, "default": 0.9,
                "label_key": "conf_top_p", "widget": "slider"
            },
            "top_k": {
                "type": "int", "min": 1, "max": 100, "step": 1, "default": 40,
                "label_key": "conf_top_k", "widget": "spin"
            },
            "repetition_penalty": {
                "type": "float", "min": 1.0, "max": 2.0, "step": 0.1, "default": 1.1,
                "label_key": "conf_rep_penalty", "widget": "spin"
            },
            "do_sample": {
                "type": "bool", "default": True,
                "label_key": "conf_do_sample", "widget": "checkbox"
            }
        }
    },
    {
        "title_key": "grp_context",
        "options": {
            "max_history_turns": {
                "type": "int", "min": 0, "max": 50, "step": 1, "default": 10,
                "label_key": "conf_history_turns", "widget": "slider"
            },
            "system_prompt": {
                "type": "str", "default": "You are a helpful AI assistant.",
                "label_key": "conf_sys_prompt", "widget": "textarea"
            }
        }
    },
    {
        "title_key": "grp_advanced",
        "options": {
            "enable_thinking": {
                "type": "bool", "default": True,
                "label_key": "conf_enable_thinking", "widget": "checkbox"
            },
            "add_generation_prompt": {
                "type": "bool", "default": True,
                "label_key": "conf_add_gen_prompt", "widget": "checkbox"
            },
            "skip_special_tokens": {
                "type": "bool", "default": True,
                "label_key": "conf_skip_special", "widget": "checkbox"
            }
        }
    }
]
