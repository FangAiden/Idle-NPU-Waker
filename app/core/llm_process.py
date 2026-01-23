import time
import traceback

from app.config import DEFAULT_CONFIG
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
                    _, final_dev = runtime.ensure_loaded(
                        src, mid, path, dev, max_prompt_len, progress_cb=progress
                    )
                    res_queue.put({"type": "loaded", "mid": mid, "dev": final_dev})
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

                supported_keys = resolve_supported_setting_keys(
                    model_name=runtime.model_path.name if runtime.model_path else None,
                    model_path=str(runtime.model_path) if runtime.model_path else None,
                )
                if supported_keys:
                    gen_params = {k: v for k, v in gen_params.items() if k in supported_keys}

                try:
                    prompt = runtime.tokenizer.apply_chat_template(
                        messages,
                        add_generation_prompt=add_gen_prompt,
                    )
                except Exception:
                    prompt = ""
                    for msg in messages:
                        prompt += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
                    if add_gen_prompt:
                        prompt += "<|im_start|>assistant\n"

                token_count = 0
                start_time = time.time()

                if ov_genai is None:
                    try:
                        import openvino_genai as ov_genai
                    except Exception as e:
                        res_queue.put({"type": "error", "msg": f"Init Error: {str(e)}"})
                        continue

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

                    runtime.pipe.generate(prompt, generation_config=gen_cfg, streamer=streamer)
                except Exception as e:
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
