import multiprocessing
import threading
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from app.core.llm_process import llm_process_entry

class AIWorker(QObject):
    # 保持原有信号定义不变，兼容 UI层
    signal_token = pyqtSignal(str)
    signal_finished = pyqtSignal()
    signal_error = pyqtSignal(str)
    signal_model_loaded = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        # 使用 'spawn' 启动方式，这对 Windows 是必须的，也能避免 Linux 下的 fork 问题
        self.ctx = multiprocessing.get_context('spawn')
        self.cmd_queue = self.ctx.Queue()
        self.res_queue = self.ctx.Queue()
        self.stop_event = self.ctx.Event()
        
        self.process = None
        self.monitor_thread = None
        self._is_running = True

    def start_process_if_needed(self):
        if self.process is None or not self.process.is_alive():
            self.process = self.ctx.Process(
                target=llm_process_entry,
                args=(self.cmd_queue, self.res_queue, self.stop_event),
                daemon=True # 设置为守护进程，主程序退出时自动结束
            )
            self.process.start()
            
            # 启动一个后台线程来监听子进程发回的消息
            # 注意：不能在 Qt 主线程里 while True 监听，会卡死 UI
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()

    def _monitor_loop(self):
        """后台线程：不断从队列取消息并触发 Qt 信号"""
        while self._is_running:
            try:
                # 阻塞式获取，不会消耗 CPU
                msg = self.res_queue.get()
                
                msg_type = msg.get("type")
                
                if msg_type == "token":
                    self.signal_token.emit(msg["token"])
                elif msg_type == "finished":
                    self.signal_finished.emit()
                elif msg_type == "loaded":
                    self.signal_model_loaded.emit(msg["mid"], msg["dev"])
                elif msg_type == "error":
                    self.signal_error.emit(msg["msg"])
            except (EOFError, BrokenPipeError):
                break # 进程可能已关闭
            except Exception as e:
                print(f"Monitor Loop Error: {e}")

    @pyqtSlot(str, str, str, str)
    def load_model(self, source, model_id, model_dir, device):
        self.start_process_if_needed()
        self.cmd_queue.put({
            "type": "load",
            "args": (source, model_id, model_dir, device)
        })

    @pyqtSlot(list, dict)
    def generate(self, messages, ui_config):
        self.start_process_if_needed()
        self.cmd_queue.put({
            "type": "generate",
            "messages": messages,
            "config": ui_config
        })

    @pyqtSlot()
    def stop(self):
        # 设置共享事件，子进程中的 streamer_cb 会检测到并停止
        self.stop_event.set()

    def cleanup(self):
        self._is_running = False
        if self.process:
            self.cmd_queue.put(None) # 发送退出指令
            self.process.join(timeout=1)
            if self.process.is_alive():
                self.process.terminate()