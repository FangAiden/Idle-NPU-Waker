# Idle NPU Waker

[简体中文](README_zh.md) | **English**

**Idle NPU Waker** is a local AI chat client built with **Python** and a Web UI.
It integrates **Intel OpenVINO GenAI** for AI PCs with NPUs (e.g. Intel Core Ultra) and provides fast local inference with CPU/GPU fallback.

> **New:** Reasoning models (e.g. DeepSeek-R1) are supported. Outputs with `<think>` are shown in a collapsible Thinking panel.

![Application Screenshot](assets/screenshot1.png)
![Application Screenshot](assets/screenshot2.png)

---

## Highlights

- **Multi-device inference:** NPU / GPU / CPU with automatic fallback.
- **Model management:** local scan, ModelScope download, per-model settings from `generation_config.json` and `app/model_settings.json`.
- **Welcome flow:** load a model before chatting, with a top-bar model switcher.
- **Streaming chat:** token streaming, temporary chats, edit/retry/copy actions.
- **Rich rendering:** Markdown, Mermaid, and KaTeX math.
- **Performance panels:** tokens/s, model memory, download status, draggable NPU monitor (when available).
- **File attachments:** attach text files (512 KB per file) and send to the model.

---

## ModelScope Download Suggestions

Paste any ModelScope repo id in the download panel. Examples:

- `OpenVINO/Qwen3-8B-int4-cw-ov`
- `OpenVINO/DeepSeek-R1-Distill-Qwen-1.5B-int4-cw-ov`
- `OpenVINO/DeepSeek-R1-Distill-Qwen-7B-int4-cw-ov`
- `OpenVINO/Phi-3.5-mini-instruct-int4-cw-ov`
- `OpenVINO/Mistral-7B-Instruct-v0.2-int4-cw-ov`
- `OpenVINO/Phi-3-mini-4k-instruct-int4-cw-ov`
- `OpenVINO/Mistral-7B-Instruct-v0.3-int4-cw-ov`
- `OpenVINO/gpt-j-6b-int4-cw-ov`
- `OpenVINO/falcon-7b-instruct-int4-cw-ov`

---

## Requirements

- **OS:** Windows 10 / 11 (recommended), Linux
- **Python:** 3.10 - 3.12
- **Key dependencies:**
  - `openvino >= 2025.1.0`
  - `openvino-genai >= 2025.1.0`
  - `openvino-tokenizers >= 2025.1.0`
  - `modelscope`
  - `fastapi`, `uvicorn`

---

## Installation & Usage

### 1. Clone Repository

```bash
git clone https://github.com/FangAiden/Idle-NPU-Waker.git
cd Idle-NPU-Waker
```

### 2. Install Dependencies

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run Web UI (FastAPI + Frontend)

```bash
python main.py
```

Or:

```bash
python backend/server.py
```

Open `http://127.0.0.1:8000` in your browser. The API is available under `/api`.

### 4. Build EXE (Optional)

```bash
python build.py
```

Output: `dist/IdleNPUWaker.exe`

---

## Project Structure

```text
Idle-NPU-Waker/
├─ main.py                  # Web entry
├─ build.py                 # PyInstaller build script (optional)
├─ backend/                 # FastAPI backend + NPU monitor
├─ frontend/                # Web UI assets
├─ models/                  # Model storage (auto-generated)
├─ .download_temp/          # Download cache
├─ app/
│  ├─ config.py             # Global config
│  ├─ core/                 # OpenVINO runtime + workers
│  ├─ utils/                # Model scanning and helpers
│  └─ model_settings.json   # Per-model settings schema
└─ requirements.txt
```

---

## License

GPLv3 License
