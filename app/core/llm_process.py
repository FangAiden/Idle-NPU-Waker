import json
import time
import traceback

import base64
import io
from pathlib import Path
from typing import Optional

def _decode_image_data(data_url: str):
    if not data_url:
        return None
    raw = None
    if data_url.startswith("data:"):
        try:
            _, b64 = data_url.split(",", 1)
        except ValueError:
            return None
        try:
            raw = base64.b64decode(b64, validate=False)
        except Exception:
            return None
    else:
        try:
            raw = base64.b64decode(data_url, validate=False)
        except Exception:
            return None
    if raw is None:
        return None
    try:
        from PIL import Image
        import numpy as np
        import openvino as ov
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        array = np.array(image)
        return ov.Tensor(array)
    except Exception:
        return None

def _strip_attachment_block(text: str) -> str:
    if not text:
        return ""
    marker = "\n\n[File]"
    if marker in text:
        text = text.split(marker, 1)[0]
    return text.strip()

def _extract_last_user_prompt(messages):
    for msg in reversed(messages or []):
        if msg.get("role") == "user":
            return _strip_attachment_block(str(msg.get("content", "")))
    if messages:
        return _strip_attachment_block(str(messages[-1].get("content", "")))
    return ""

def _infer_image_max_sequence_length(model_path: Optional[Path]) -> Optional[int]:
    if not model_path:
        return None
    candidates = [
        Path(model_path) / "tokenizer_2" / "tokenizer_config.json",
        Path(model_path) / "tokenizer" / "tokenizer_config.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        value = data.get("model_max_length") or data.get("max_length")
        if isinstance(value, int) and value > 0:
            return value
    return None

def _apply_image_max_sequence_length(pipe, max_sequence_length: int) -> bool:
    try:
        cfg = pipe.get_generation_config()
        if not hasattr(cfg, "max_sequence_length"):
            return False
        cfg.max_sequence_length = int(max_sequence_length)
        pipe.set_generation_config(cfg)
        return True
    except Exception:
        return False

def _image_tensor_to_attachments(image_tensor, max_bytes: int):
    try:
        import numpy as np
        from PIL import Image
    except Exception:
        return []

    data = getattr(image_tensor, "data", image_tensor)
    try:
        arr = np.array(data)
    except Exception:
        return []

    if arr.ndim == 3:
        arr = arr[None, ...]
    if arr.ndim != 4:
        return []

    attachments = []
    for idx, img in enumerate(arr, start=1):
        if img.ndim != 3:
            continue
        if img.shape[0] in (1, 3) and img.shape[-1] not in (1, 3):
            img = np.transpose(img, (1, 2, 0))
        if img.dtype != np.uint8:
            max_val = float(img.max()) if img.size else 0.0
            if max_val <= 1.0:
                img = img * 255.0
            img = np.clip(img, 0, 255).astype(np.uint8)
        try:
            image = Image.fromarray(img)
        except Exception:
            continue
        buffer = io.BytesIO()
        try:
            image.save(buffer, format="PNG")
        except Exception:
            continue
        raw = buffer.getvalue()
        if max_bytes and len(raw) > max_bytes:
            continue
        b64 = base64.b64encode(raw).decode("ascii")
        attachments.append({
            "name": f"generated_{idx}.png",
            "content": f"data:image/png;base64,{b64}",
            "kind": "image",
            "mime": "image/png",
            "truncated": False,
        })
    return attachments

def _extract_vlm_images(messages):
    last_user = None
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user = msg
            break
    if not last_user:
        return []
    attachments = last_user.get("attachments") or []
    images = []
    for att in attachments:
        if (att.get("kind") or "").lower() != "image":
            continue
        tensor = _decode_image_data(str(att.get("content", "")))
        if tensor is not None:
            images.append(tensor)
    return images

def _is_prompt_too_long(err: Exception) -> bool:
    if not err:
        return False
    msg = str(err)
    return "m_max_prompt_len" in msg or "MAX_PROMPT_LEN" in msg or "prompt_len" in msg

def _is_image_seq_mismatch(err: Exception) -> bool:
    if not err:
        return False
    msg = str(err)
    return ("max_sequence_length" in msg and "reshape" in msg and "T5EncoderModel" in msg)

from app.config import DEFAULT_CONFIG, MAX_IMAGE_BYTES
from app.utils.config_loader import resolve_supported_setting_keys


def llm_process_entry(cmd_queue, res_queue, stop_event):
    """
    Child process entry.
    cmd_queue: receive commands (load, generate, exit)
    res_queue: send results (token, finished, error)
    stop_event: used to stop generation
    """
    try:
        from app.core.runtime import RuntimeState
    except Exception as e:
        res_queue.put({"type": "error", "msg": f"Init Error: {str(e)}"})
        return

    runtime = RuntimeState()
    ov_genai = None

    while True:
        try:
            cmd = cmd_queue.get()

            if cmd is None:
                break

            cmd_type = cmd.get("type")

            if cmd_type == "load":
                try:
                    src, mid, path, dev, max_prompt_len = cmd["args"]

                    def progress(stage: str, message: str) -> None:
                        res_queue.put({"type": "load_stage", "stage": stage, "message": message})

                    res_queue.put({"type": "load_stage", "stage": "start", "message": "Starting"})
                    _, final_dev, model_kind = runtime.ensure_loaded(
                        src,
                        mid,
                        path,
                        dev,
                        max_prompt_len=max_prompt_len,
                        progress_cb=progress,
                    )
                    res_queue.put({"type": "loaded", "mid": mid, "dev": final_dev, "kind": model_kind})
                except Exception as e:
                    res_queue.put({"type": "error", "msg": f"Load Error: {str(e)}"})

            elif cmd_type == "generate":
                if not runtime.pipe:
                    res_queue.put({"type": "error", "msg": "Model not loaded in process"})
                    continue

                messages = cmd["messages"]
                ui_config = cmd["config"]

                stop_event.clear()

                gen_params = DEFAULT_CONFIG.copy()
                if ui_config:
                    gen_params.update(ui_config)

                add_gen_prompt = gen_params.pop("add_generation_prompt", True)
                _ = gen_params.pop("enable_thinking", True)

                for k in ["system_prompt", "max_history_turns", "skip_special_tokens"]:
                    if k in gen_params:
                        gen_params.pop(k)

                supported_keys = None
                if runtime.model_kind == "image":
                    supported_keys = runtime.supported_keys
                if not supported_keys:
                    supported_keys = resolve_supported_setting_keys(
                        model_name=runtime.model_path.name if runtime.model_path else None,
                        model_path=str(runtime.model_path) if runtime.model_path else None,
                    )
                if supported_keys:
                    gen_params = {k: v for k, v in gen_params.items() if k in supported_keys}

                if ov_genai is None:
                    try:
                        import openvino_genai as ov_genai
                    except Exception as e:
                        res_queue.put({"type": "error", "msg": f"Init Error: {str(e)}"})
                        continue

                if runtime.model_kind == "image":
                    prompt = _extract_last_user_prompt(messages)
                    if not prompt:
                        res_queue.put({"type": "error", "msg": "Gen Error: Empty prompt"})
                        continue
                    if isinstance(gen_params.get("negative_prompt"), str) and not gen_params["negative_prompt"].strip():
                        gen_params.pop("negative_prompt", None)
                    rng_seed = gen_params.get("rng_seed")
                    if isinstance(rng_seed, (int, float)) and rng_seed < 0:
                        gen_params.pop("rng_seed", None)
                    if rng_seed is None:
                        gen_params.pop("rng_seed", None)
                    raw_max_seq = gen_params.pop("max_sequence_length", None)
                    max_seq = raw_max_seq if isinstance(raw_max_seq, int) and raw_max_seq > 0 else None
                    if max_seq is None:
                        max_seq = runtime.image_max_sequence_length or _infer_image_max_sequence_length(runtime.model_path)
                    if isinstance(max_seq, int) and max_seq > 0:
                        if runtime.image_max_sequence_length != max_seq:
                            try:
                                runtime.ensure_loaded(
                                    runtime.model_source,
                                    runtime.model_id,
                                    runtime.model_dir,
                                    runtime.device,
                                    max_prompt_len=runtime.max_prompt_len or 16384,
                                    image_max_sequence_length=max_seq,
                                )
                            except Exception as e:
                                res_queue.put({"type": "error", "msg": f"Gen Error: Failed to reload image pipeline: {str(e)}"})
                                continue
                        gen_params["max_sequence_length"] = max_seq
                    start_time = time.time()
                    attachments = []
                    retry_on_mismatch = True
                    try:
                        image_tensor = runtime.pipe.generate(prompt, **gen_params)
                        attachments = _image_tensor_to_attachments(image_tensor, MAX_IMAGE_BYTES)
                        if attachments:
                            res_queue.put({"type": "image", "attachments": attachments})
                    except Exception as e:
                        if retry_on_mismatch and _is_image_seq_mismatch(e) and isinstance(max_seq, int) and max_seq > 0:
                            retry_on_mismatch = False
                            try:
                                runtime.ensure_loaded(
                                    runtime.model_source,
                                    runtime.model_id,
                                    runtime.model_dir,
                                    runtime.device,
                                    max_prompt_len=runtime.max_prompt_len or 16384,
                                    image_max_sequence_length=max_seq,
                                    cache_bust=f"retry{int(time.time())}",
                                )
                                image_tensor = runtime.pipe.generate(prompt, **gen_params)
                                attachments = _image_tensor_to_attachments(image_tensor, MAX_IMAGE_BYTES)
                                if attachments:
                                    res_queue.put({"type": "image", "attachments": attachments})
                            except Exception as retry_err:
                                res_queue.put({"type": "error", "msg": f"Gen Error: {str(retry_err)}"})
                        else:
                            res_queue.put({"type": "error", "msg": f"Gen Error: {str(e)}"})
                    finally:
                        elapsed = time.time() - start_time
                        res_queue.put({
                            "type": "finished",
                            "stats": {
                                "tokens": 0,
                                "time": round(elapsed, 2),
                                "speed": 0,
                                "images": len(attachments),
                            },
                        })
                    continue

                token_count = 0
                start_time = time.time()
                prompt = ""

                def streamer_cb(sub_text):
                    nonlocal token_count
                    if stop_event.is_set():
                        return True
                    token_count += 1
                    res_queue.put({"type": "token", "token": sub_text})
                    return False

                try:
                    gen_cfg = ov_genai.GenerationConfig(**gen_params)
                    streamer = ov_genai.TextStreamer(runtime.tokenizer, streamer_cb)

                    def run_generate(msgs):
                        nonlocal token_count, start_time, prompt
                        try:
                            prompt = runtime.tokenizer.apply_chat_template(
                                msgs,
                                add_generation_prompt=add_gen_prompt,
                            )
                        except Exception:
                            prompt = ""
                            for msg in msgs:
                                prompt += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
                            if add_gen_prompt:
                                prompt += "<|im_start|>assistant\n"
                        token_count = 0
                        start_time = time.time()
                        if runtime.model_kind == "vlm":
                            images = _extract_vlm_images(msgs)
                            if images:
                                runtime.pipe.generate(prompt, images=images, generation_config=gen_cfg, streamer=streamer)
                            else:
                                runtime.pipe.generate(prompt, generation_config=gen_cfg, streamer=streamer)
                        else:
                            runtime.pipe.generate(prompt, generation_config=gen_cfg, streamer=streamer)

                    run_generate(messages)
                except Exception as e:
                    limit = getattr(runtime, "max_prompt_len", None)
                    if runtime.model_kind == "vlm" and _is_prompt_too_long(e):
                        hint = f"VLM prompt too long (limit {limit or 1024}). Reduce history or shorten input."
                        res_queue.put({"type": "error", "msg": f"Gen Error: {hint}"})
                    else:
                        res_queue.put({"type": "error", "msg": f"Gen Error: {str(e)}"})
                finally:
                    elapsed = time.time() - start_time
                    speed = token_count / elapsed if elapsed > 0 else 0
                    res_queue.put({
                        "type": "finished",
                        "stats": {
                            "tokens": token_count,
                            "time": round(elapsed, 2),
                            "speed": round(speed, 2),
                        },
                    })

        except Exception as e:
            res_queue.put({"type": "error", "msg": f"Process Crash: {str(e)}"})
            traceback.print_exc()
