"""
模型预设配置
注意：通用的生成参数 (如 temperature, top_p, max_new_tokens) 现在优先从
模型目录下的 generation_config.json 动态读取。
此处仅保留下载列表以及应用层特定的配置（如系统提示词、思考模式开关）。
"""

NPU_COLLECTION_URL = (
    "https://www.modelscope.cn/collections/LLMs-optimized-for-NPU-13ad4be17f8740"
)

NPU_COLLECTION_MODELS = [
    {
        "name": "gpt-j-6b-int4-cw-ov",
        "repo_id": "OpenVINO/gpt-j-6b-int4-cw-ov",
        "downloads": 163,
        "license": "apache-2.0",
        "libraries": ["pytorch", "openvino"],
        "model_id": 505019,
    },
    {
        "name": "DeepSeek-R1-Distill-Qwen-7B-int4-cw-ov",
        "repo_id": "OpenVINO/DeepSeek-R1-Distill-Qwen-7B-int4-cw-ov",
        "downloads": 199,
        "license": "mit",
        "libraries": ["pytorch", "openvino"],
        "model_id": 505027,
    },
    {
        "name": "DeepSeek-R1-Distill-Qwen-1.5B-int4-cw-ov",
        "repo_id": "OpenVINO/DeepSeek-R1-Distill-Qwen-1.5B-int4-cw-ov",
        "downloads": 212,
        "license": "mit",
        "libraries": ["pytorch", "openvino"],
        "model_id": 505047,
    },
    {
        "name": "Phi-3.5-mini-instruct-int4-cw-ov",
        "repo_id": "OpenVINO/Phi-3.5-mini-instruct-int4-cw-ov",
        "downloads": 223,
        "license": "mit",
        "libraries": ["pytorch", "openvino"],
        "model_id": 505065,
    },
    {
        "name": "Qwen3-8B-int4-cw-ov",
        "repo_id": "OpenVINO/Qwen3-8B-int4-cw-ov",
        "downloads": 331,
        "license": "apache-2.0",
        "libraries": ["pytorch", "openvino"],
        "model_id": 505045,
    },
    {
        "name": "falcon-7b-instruct-int4-cw-ov",
        "repo_id": "OpenVINO/falcon-7b-instruct-int4-cw-ov",
        "downloads": 165,
        "license": "apache-2.0",
        "libraries": ["pytorch", "openvino"],
        "model_id": 505059,
    },
    {
        "name": "Mistral-7B-Instruct-v0.2-int4-cw-ov",
        "repo_id": "OpenVINO/Mistral-7B-Instruct-v0.2-int4-cw-ov",
        "downloads": 175,
        "license": "apache-2.0",
        "libraries": ["pytorch", "openvino"],
        "model_id": 505050,
    },
    {
        "name": "Phi-3-mini-4k-instruct-int4-cw-ov",
        "repo_id": "OpenVINO/Phi-3-mini-4k-instruct-int4-cw-ov",
        "downloads": 220,
        "license": "mit",
        "libraries": ["pytorch", "openvino"],
        "model_id": 505053,
    },
    {
        "name": "Mistral-7B-Instruct-v0.3-int4-cw-ov",
        "repo_id": "OpenVINO/Mistral-7B-Instruct-v0.3-int4-cw-ov",
        "downloads": 175,
        "license": "apache-2.0",
        "libraries": ["pytorch", "openvino"],
        "model_id": 505062,
    },
]

PRESET_MODELS = [model["repo_id"] for model in NPU_COLLECTION_MODELS]

MODEL_SPECIFIC_CONFIGS = {
    "OpenVINO/Qwen3-8B-int4-cw-ov": {
        "grp_context": {
            "system_prompt": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."
        },
        "grp_advanced": {
            "add_generation_prompt": True,
            "enable_thinking": False
        }
    },
    "OpenVINO/DeepSeek-R1-Distill-Qwen-1.5B-int4-cw-ov": {
        "grp_context": {
            "system_prompt": "You are a helpful assistant. You should think before you answer."
        },
        "grp_advanced": {
            "add_generation_prompt": True,
            "enable_thinking": True
        }
    },
    "OpenVINO/DeepSeek-R1-Distill-Qwen-7B-int4-cw-ov": {
        "grp_context": {
            "system_prompt": "You are a helpful assistant. You should think before you answer."
        },
        "grp_advanced": {
            "add_generation_prompt": True,
            "enable_thinking": True
        }
    }
}
