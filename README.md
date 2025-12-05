# Idle NPU Waker

**Idle NPU Waker** 是一个基于 **Python** 与 **PyQt6** 构建的现代化本地 AI 聊天客户端。应用深度集成 **Intel OpenVINO™ GenAI** 工具链，专为配备 Intel Core Ultra（Meteor Lake / Lunar Lake）等具备 **NPU（神经网络处理单元）** 的 AI PC 优化，带来低延迟、低功耗的完全离线大模型推理体验。

> **新特性**：适配推理模型，支持可视化展示思维链（Chain of Thought），提供折叠/展开的深度思考 UI 体验。

![应用运行截图](assets/screenshot1.png)

------------------------------------------------------------------------

## 核心特性

### 极致本地加速与稳定性
-   **多设备异构推理**：原生支持 Intel **NPU**、iGPU（Intel Arc）与 CPU 推理，充分利用硬件性能。
-   **智能回退机制**：若指定设备（如 NPU）初始化失败，自动无缝回退至 CPU，确保程序在各种环境下都能稳定运行。
-   **显存安全管理**：在切换模型时执行深度显存清理与垃圾回收（GC），防止因显存残留导致的程序闪退。

### 深度思考 UI (DeepSeek R1 适配)
-   **思维链可视化**：自动解析模型输出的 `<think>` 标签，将“思考过程”与“正式回答”分离显示，清晰呈现 AI 的推理逻辑。
-   **交互式折叠**：思考内容支持折叠/展开，并显示推理耗时，既保持界面整洁又能深入探究 AI 思路。

### 一站式模型管理
-   **独立下载进程**：下载任务在独立进程中运行，彻底杜绝界面卡顿，支持随时暂停/取消/断点续传。
-   **魔搭社区集成**：内置 ModelScope 下载器，自动处理文件结构，下载即用，无需手动解压或配置。
-   **智能扫描**：自动递归扫描目录，智能识别有效的 OpenVINO 模型（基于 `openvino_model.xml` 和 `tokenizer` 文件特征）。

### 现代化交互
-   **流式打字机**：实时渲染生成的 Token，提供流畅的阅读体验。
-   **富文本支持**：基于 Markdown 渲染，支持代码块高亮与格式化文本。
-   **多会话管理**：支持创建新对话、历史记录自动保存与右键删除管理。

------------------------------------------------------------------------

## 预设支持模型

项目内置了以下针对 OpenVINO 优化的量化模型配置，可直接在应用内下载：

* **DeepSeek 系列**: `DeepSeek-R1-Distill-Qwen-1.5B`, `DeepSeek-R1-Distill-Qwen-7B`
* **Qwen 系列**: `Qwen3-8B-int4-cw-ov`
* **Phi 系列**: `Phi-3.5-mini-instruct`, `Phi-3-mini-4k-instruct`
* **Mistral 系列**: `Mistral-7B-Instruct-v0.2`, `Mistral-7B-Instruct-v0.3`
* **其他**: `gpt-j-6b`, `falcon-7b`

------------------------------------------------------------------------

## 环境要求

-   **操作系统**：Windows 10 / 11（推荐），Linux
-   **Python**：3.10 - 3.12
-   **关键依赖库**：
    -   `openvino-genai >= 2025.1.0` (必须)
    -   `PyQt6`
    -   `modelscope`

------------------------------------------------------------------------

## 安装与运行

### 1. 克隆仓库

```bash
git clone https://github.com/FangAiden/Idle-NPU-Waker.git
cd Idle-NPU-Waker
```

### 2. 安装依赖

建议使用虚拟环境：

```bash
# 创建并激活虚拟环境 (Windows)
python -m venv venv
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 启动应用

```bash
python main.py
```

### 4. 打包为 EXE (可选)

项目提供了一键打包脚本，自动处理 OpenVINO 和 ModelScope 的隐式依赖，生成独立的 `.exe` 文件：

```bash
python build.py
```

打包产物将位于 `dist/IdleNPUWaker.exe`。

-----

## 项目结构

```text
Idle-NPU-Waker/
├── main.py                  # 主入口 (兼任下载进程入口)
├── build.py                 # PyInstaller 一键打包脚本
├── models/                  # 模型存储目录 (自动生成)
├── .download_temp/          # 下载缓存目录
├── app/
│   ├── config.py            # 全局配置与预设模型列表
│   ├── core/                # 核心后端
│   │   ├── runtime.py       # OpenVINO GenAI 封装与显存安全管理
│   │   ├── llm_worker.py    # 异步推理线程
│   │   ├── downloader.py    # 独立下载进程管理器
│   │   └── download_script.py # 独立运行的下载脚本
│   ├── ui/                  # 界面层
│   │   ├── chat_window.py   # 主窗口逻辑
│   │   ├── message_bubble.py# 消息气泡 (含 DeepSeek 思考内容渲染)
│   │   ├── sidebar.py       # 侧边栏与设置
│   │   └── resources.py     # 嵌入式图标资源
│   └── utils/               # 工具集
│       └── scanner.py       # 模型目录智能递归扫描
└── requirements.txt         # 依赖清单
```

-----

## 许可证

GPLv3 License
