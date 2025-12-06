"""
模型预设配置
注意：通用的生成参数 (如 temperature, top_p, max_new_tokens) 现在优先从
模型目录下的 generation_config.json 动态读取。
此处仅保留下载列表以及应用层特定的配置（如系统提示词、思考模式开关）。
"""

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