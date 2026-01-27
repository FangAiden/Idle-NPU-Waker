import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Set

SETTINGS_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "model_settings.json"

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

def load_model_settings_schema(path: Optional[Path] = None) -> Dict[str, Any]:
    schema_path = path or SETTINGS_SCHEMA_PATH
    if not schema_path.exists():
        return {}
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"Error reading model_settings.json: {e}")
        return {}

def scan_generation_config_keys(model_path: Optional[str]) -> Set[str]:
    if not model_path:
        return set()
    path = Path(model_path)
    gen_config_path = path / "generation_config.json"
    if not gen_config_path.exists():
        return set()
    try:
        with open(gen_config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.keys()) if isinstance(data, dict) else set()
    except Exception as e:
        print(f"Error reading generation_config.json: {e}")
        return set()

def _collect_all_setting_keys() -> Set[str]:
    try:
        from app.config import CONFIG_GROUPS
    except Exception:
        return set()
    keys = set()
    for group in CONFIG_GROUPS:
        for key in group.get("options", {}).keys():
            keys.add(key)
    return keys

def _infer_image_setting_keys() -> Set[str]:
    try:
        import openvino_genai as ov_genai
        cfg = ov_genai.ImageGenerationConfig()
        keys = set()
        for name in dir(cfg):
            if name.startswith("_"):
                continue
            try:
                value = getattr(cfg, name)
            except Exception:
                continue
            if callable(value):
                continue
            keys.add(name)
        if keys:
            return keys
    except Exception:
        pass
    return {
        "negative_prompt",
        "num_inference_steps",
        "guidance_scale",
        "width",
        "height",
        "num_images_per_prompt",
        "rng_seed",
    }

def _match_model_rule(rule_id: str, rule: Dict[str, Any],
                      model_name: Optional[str], model_path: Optional[str]) -> bool:
    if not rule_id:
        return False
    candidates = []
    if model_name:
        candidates.append(model_name)
    if model_path:
        candidates.append(Path(model_path).name)
    for alias in rule.get("aliases", []) or []:
        candidates.append(alias)

    rule_norm = str(rule_id).lower()
    rule_base = str(Path(rule_id).name).lower()

    for cand in candidates:
        if not cand:
            continue
        cand_norm = str(cand).lower()
        if cand_norm == rule_norm or cand_norm == rule_base:
            return True
        if rule_norm in cand_norm or cand_norm in rule_norm:
            return True
    return False

def resolve_supported_setting_keys(model_name: Optional[str] = None,
                                   model_path: Optional[str] = None,
                                   all_setting_keys: Optional[Set[str]] = None) -> Set[str]:
    if model_path:
        try:
            from app.utils.model_type import detect_model_kind
            if detect_model_kind(Path(model_path)) == "image":
                return _infer_image_setting_keys()
        except Exception:
            pass

    schema = load_model_settings_schema()
    defaults = schema.get("defaults", {})
    model_rules = schema.get("models", {})

    matched_rule = None
    for rule_id, rule in model_rules.items():
        if _match_model_rule(rule_id, rule, model_name, model_path):
            matched_rule = rule
            break

    all_keys = set(all_setting_keys) if all_setting_keys is not None else _collect_all_setting_keys()

    mode = (matched_rule or {}).get("mode", defaults.get("mode", "all"))
    supported: Set[str]

    if mode == "auto":
        supported = scan_generation_config_keys(model_path)
        if not supported and all_keys:
            supported = set(all_keys)
    elif mode == "list":
        supported = set((matched_rule or {}).get("supported_keys") or defaults.get("supported_keys") or [])
    elif mode == "none":
        supported = set()
    else:
        supported = set(all_keys)

    app_keys = defaults.get("app_keys", [])
    if matched_rule and "app_keys" in matched_rule:
        app_keys = matched_rule.get("app_keys") or []

    supported |= set(app_keys)

    if matched_rule:
        supported |= set(matched_rule.get("include", []) or [])
        supported -= set(matched_rule.get("exclude", []) or [])

    if all_keys:
        supported &= set(all_keys)

    if not supported and all_keys:
        supported = set(all_keys)

    return supported
