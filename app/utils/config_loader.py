import json
import os
from pathlib import Path

def load_model_json_configs(model_path):
    """
    尝试读取模型目录下的 config.json 和 generation_config.json
    返回一个包含合并配置的字典
    """
    path = Path(model_path)
    merged_config = {}
    
    config_path = path / "config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                merged_config["model_max_length"] = data.get("max_position_embeddings", 
                                                    data.get("seq_length", 8192))
                merged_config["vocab_size"] = data.get("vocab_size", 0)
        except Exception as e:
            print(f"Error reading config.json: {e}")

    gen_config_path = path / "generation_config.json"
    if gen_config_path.exists():
        try:
            with open(gen_config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for key in ["temperature", "top_p", "top_k", "repetition_penalty", 
                            "max_new_tokens", "do_sample", "no_repeat_ngram_size"]:
                    if key in data:
                        merged_config[key] = data[key]
                
                if "eos_token_id" in data:
                    merged_config["eos_token_id"] = data["eos_token_id"]
                    
        except Exception as e:
            print(f"Error reading generation_config.json: {e}")
            
    return merged_config