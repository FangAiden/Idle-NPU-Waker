import openvino_genai as ov_genai
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from app.core.runtime import RuntimeState

class AIWorker(QObject):
    """
    后台 AI Worker：负责执行耗时的模型加载和推理任务。
    配合 moveToThread 使用。
    """
    # 定义信号
    signal_token = pyqtSignal(str)                # 生成的文本片段
    signal_finished = pyqtSignal()                # 生成结束
    signal_error = pyqtSignal(str)                # 发生错误
    signal_model_loaded = pyqtSignal(str, str)    # 模型加载完成 (model_id, device)

    def __init__(self, runtime: RuntimeState):
        super().__init__()
        self.runtime = runtime
        self._stop_flag = False

    @pyqtSlot(str, str, str, str)
    def load_model(self, source, model_id, model_dir, device):
        """
        加载模型槽函数
        """
        try:
            # 这里的 ensure_loaded 可能会耗时较长
            path, dev = self.runtime.ensure_loaded(source, model_id, model_dir, device)
            self.signal_model_loaded.emit(self.runtime.model_id, dev)
        except Exception as e:
            self.signal_error.emit(f"模型加载失败: {str(e)}")

    @pyqtSlot(str, dict)
    def generate(self, prompt, config):
        """
        文本生成槽函数
        """
        if not self.runtime.pipe:
            self.signal_error.emit("模型未加载")
            self.signal_finished.emit()
            return

        self._stop_flag = False

        # 定义流式回调（在子线程运行）
        def streamer_cb(sub_text):
            if self._stop_flag:
                return True # 返回 True 停止生成
            self.signal_token.emit(sub_text)
            return False

        try:
            # 配置生成参数
            gen_cfg = ov_genai.GenerationConfig(
                max_new_tokens=config.get("max_new_tokens", 512),
                temperature=config.get("temperature", 0.8),
                top_p=config.get("top_p", 0.9),
                do_sample=config.get("do_sample", True)
            )
            
            # 创建 Streamer
            streamer = ov_genai.TextStreamer(self.runtime.tokenizer, streamer_cb)
            
            # 开始推理（阻塞当前线程）
            self.runtime.pipe.generate(prompt, generation_config=gen_cfg, streamer=streamer)
            
        except Exception as e:
            if not self._stop_flag:
                self.signal_error.emit(f"生成出错: {str(e)}")
        finally:
            self.signal_finished.emit()

    @pyqtSlot()
    def stop(self):
        """设置停止标志"""
        self._stop_flag = True