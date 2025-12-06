import multiprocessing
import traceback
import openvino_genai as ov_genai
from app.core.runtime import RuntimeState
from app.config import DEFAULT_CONFIG

def llm_process_entry(cmd_queue, res_queue, stop_event):
    """
    独立进程的入口函数
    :param cmd_queue: 接收主进程指令的队列 (load, generate, exit)
    :param res_queue: 发送结果回主进程的队列 (token, finished, error)
    :param stop_event: 用于控制停止生成的共享事件
    """
    runtime = RuntimeState()
    
    while True:
        try:
            cmd = cmd_queue.get()
            
            if cmd is None:
                break
            
            cmd_type = cmd.get("type")
            
            if cmd_type == "load":
                try:
                    src, mid, path, dev = cmd["args"]
                    final_path, final_dev = runtime.ensure_loaded(src, mid, path, dev)
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
                    if k in gen_params: gen_params.pop(k)

                try:      
                    prompt = runtime.tokenizer.apply_chat_template(
                        messages,
                        add_generation_prompt=add_gen_prompt
                    )
                except Exception as e:
                    prompt = ""
                    for msg in messages:
                        prompt += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
                    if add_gen_prompt:
                        prompt += "<|im_start|>assistant\n"

                def streamer_cb(sub_text):
                    if stop_event.is_set():
                        return True
                    
                    res_queue.put({"type": "token", "token": sub_text})
                    return False

                try:
                    gen_cfg = ov_genai.GenerationConfig(**gen_params)
                    streamer = ov_genai.TextStreamer(runtime.tokenizer, streamer_cb)
                    
                    runtime.pipe.generate(prompt, generation_config=gen_cfg, streamer=streamer)
                except Exception as e:
                    res_queue.put({"type": "error", "msg": f"Gen Error: {str(e)}"})
                finally:
                    res_queue.put({"type": "finished"})

        except Exception as e:
            res_queue.put({"type": "error", "msg": f"Process Crash: {str(e)}"})
            traceback.print_exc()