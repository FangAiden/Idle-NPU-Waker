import os
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    # 打包环境
    ROOT_DIR = Path(sys.executable).parent.resolve()
else:
    # 开发环境
    ROOT_DIR = Path(__file__).parent.parent.resolve()

# 目录配置
MODELS_DIR = ROOT_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOAD_CACHE_DIR = ROOT_DIR / ".download_temp"
DOWNLOAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "max_history_turns": 8,
    "max_new_tokens": 512,
    "temperature": 0.8,
    "top_p": 0.9,
    "top_k": 40,
    "do_sample": True,
}

# 预设模型列表
PRESET_MODELS = [
    "OpenVINO/Qwen3-8B-int4-cw-ov",
    "OpenVINO/DeepSeek-R1-Distill-Qwen-1.5B-int4-cw-ov",
    "OpenVINO/DeepSeek-R1-Distill-Qwen-7B-int4-cw-ov",
    "OpenVINO/Phi-3.5-mini-instruct-int4-cw-ov",
    "OpenVINO/Mistral-7B-Instruct-v0.2-int4-cw-ov",
    "OpenVINO/Phi-3-mini-4k-instruct-int4-cw-ov",
    "OpenVINO/Mistral-7B-Instruct-v0.3-int4-cw-ov",
    "OpenVINO/gpt-j-6b-int4-cw-ov",
    "OpenVINO/falcon-7b-instruct-int4-cw-ov"
]