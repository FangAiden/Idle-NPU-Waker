# Idle NPU Waker

[简体中文](README_zh.md) | **English**

**Idle NPU Waker** is a modern local AI chat client built with **Python** and **PyQt6**.
The application deeply integrates the **Intel OpenVINO™ GenAI** toolchain, optimized for AI PCs equipped with **NPUs (Neural Processing Units)** such as Intel Core Ultra (Meteor Lake / Lunar Lake), delivering low‑latency, low‑power, fully offline large‑model inference.

> **✨ New Feature:** Fully adapted for reasoning models (e.g., DeepSeek‑R1), supporting Chain‑of‑Thought (CoT) visualization with a collapsible Deep Thinking UI.

![Application Screenshot](assets/screenshot1.png)

---

## Core Features

### 🚀 Extreme Local Acceleration & Stability
- **Multi‑Device Inference:** Native support for Intel **NPU**, iGPU (Intel Arc), and CPU.
- **Smart Fallback Mechanism:** Automatically falls back to CPU if the selected device fails to initialize.
- **Safe Memory Management:** Deep cleanup and garbage collection when switching models to prevent crashes caused by leftover memory.

### 🧠 Deep Thinking UI
- **Chain‑of‑Thought Visualization:** Parses `<think>` tags from model output and separates *thinking* and *final answer*.
- **Interactive Folding:** Thinking content can be expanded/collapsed and displays inference time.

### 📦 One‑Stop Model Management
- **Independent Download Process:** Runs in its own process with pause/cancel/resume and zero UI freezing.
- **ModelScope Integration:** Automatically handles file structures—ready to use immediately after download.
- **Smart Scanning:** Recursively detects valid OpenVINO models via `openvino_model.xml` and tokenizer structure.

### 🎨 Modern Interaction
- **Streaming Typewriter Effect** for real‑time token rendering.
- **Markdown Rendering** with code highlight support.
- **Multi‑Session Management** including history saving and right‑click deletion.

---

## Preset Supported Models

Downloadable directly inside the application:

- **DeepSeek Series:**  
  `DeepSeek-R1-Distill-Qwen-1.5B`, `DeepSeek-R1-Distill-Qwen-7B`
- **Qwen Series:**  
  `Qwen3-8B-int4-cw-ov`
- **Phi Series:**  
  `Phi-3.5-mini-instruct`, `Phi-3-mini-4k-instruct`
- **Mistral Series:**  
  `Mistral-7B-Instruct-v0.2`, `Mistral-7B-Instruct-v0.3`
- **Others:**  
  `gpt-j-6b`, `falcon-7b`

---

## Requirements

- **OS:** Windows 10 / 11 (recommended), Linux  
- **Python:** 3.10 – 3.12  
- **Key Dependencies:**
  - `openvino-genai >= 2025.1.0`
  - `PyQt6`
  - `modelscope`

---

## Installation & Usage

### 1. Clone Repository

```bash
git clone https://github.com/FangAiden/Idle-NPU-Waker.git
cd Idle-NPU-Waker
```

### 2. Install Dependencies

Recommended: use a virtual environment.

```bash
# Create and activate venv (Windows)
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Application

```bash
python main.py
```

### 4. Build EXE (Optional)

The project includes a one‑click build script that automatically handles  
OpenVINO & ModelScope implicit dependencies:

```bash
python build.py
```

Output file: `dist/IdleNPUWaker.exe`

---

## Project Structure

```text
Idle-NPU-Waker/
├── main.py                  # Main entry (also download process entry)
├── build.py                 # One-click PyInstaller build script
├── models/                  # Model storage (auto-generated)
├── .download_temp/          # Download cache
├── app/
│   ├── config.py            # Global config and preset model list
│   ├── core/
│   │   ├── runtime.py       # OpenVINO GenAI wrapper & memory safety
│   │   ├── llm_worker.py    # Async inference thread
│   │   ├── downloader.py    # Download process manager
│   │   └── download_script.py
│   ├── ui/
│   │   ├── chat_window.py
│   │   ├── message_bubble.py
│   │   ├── sidebar.py
│   │   └── resources.py
│   └── utils/
│       └── scanner.py       # Smart recursive model scanner
└── requirements.txt
```

---

## License

GPLv3 License
