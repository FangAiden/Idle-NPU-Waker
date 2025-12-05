import os
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    ROOT_DIR = Path(sys.executable).parent.resolve()
else:
    ROOT_DIR = Path(__file__).parent.parent.resolve()

MODELS_DIR = ROOT_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOAD_CACHE_DIR = ROOT_DIR / ".download_temp"
DOWNLOAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)

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
    "skip_special_tokens": True
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