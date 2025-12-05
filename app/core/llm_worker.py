import openvino_genai as ov_genai
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from app.core.runtime import RuntimeState
from app.config import DEFAULT_CONFIG

class AIWorker(QObject):
    signal_token = pyqtSignal(str)
    signal_finished = pyqtSignal()
    signal_error = pyqtSignal(str)
    signal_model_loaded = pyqtSignal(str, str)

    def __init__(self, runtime: RuntimeState):
        super().__init__()
        self.runtime = runtime
        self._stop_flag = False

    @pyqtSlot(str, str, str, str)
    def load_model(self, source, model_id, model_dir, device):
        try:
            path, dev = self.runtime.ensure_loaded(source, model_id, model_dir, device)
            self.signal_model_loaded.emit(self.runtime.model_id, dev)
        except Exception as e:
            self.signal_error.emit(f"模型加载失败: {str(e)}")

    @pyqtSlot(list, dict)
    def generate(self, messages, ui_config):
        if not self.runtime.pipe:
            self.signal_error.emit("模型未加载")
            self.signal_finished.emit()
            return

        self._stop_flag = False

        def streamer_cb(sub_text):
            if self._stop_flag:
                return True
            self.signal_token.emit(sub_text)
            return False

        try:
            gen_params = DEFAULT_CONFIG.copy()
            if ui_config:
                gen_params.update(ui_config)

            add_gen_prompt = gen_params.pop("add_generation_prompt", True)
            
            _ = gen_params.pop("enable_thinking", True) 
            
            for k in ["system_prompt", "max_history_turns", "skip_special_tokens"]:
                if k in gen_params: gen_params.pop(k)

            try:      
                prompt = self.runtime.tokenizer.apply_chat_template(
                    messages,
                    add_generation_prompt=add_gen_prompt
                )
            except Exception as e:
                print(f"[Worker] Template apply failed: {e}")

                prompt = ""
                for msg in messages:
                    prompt += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
                if add_gen_prompt:
                    prompt += "<|im_start|>assistant\n"

            gen_cfg = ov_genai.GenerationConfig(**gen_params)
            
            streamer = ov_genai.TextStreamer(self.runtime.tokenizer, streamer_cb)
            
            self.runtime.pipe.generate(prompt, generation_config=gen_cfg, streamer=streamer)
            
        except Exception as e:
            if not self._stop_flag:
                self.signal_error.emit(f"生成出错: {str(e)}")
        finally:
            self.signal_finished.emit()

    @pyqtSlot()
    def stop(self):
        self._stop_flag = True