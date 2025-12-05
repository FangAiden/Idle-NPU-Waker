import gc
import re
import time
import sys
from pathlib import Path
from typing import Optional, Tuple
import openvino_genai as ov_genai
from app.config import MODELS_DIR

def log_to_file(msg):
    try:
        with open("runtime.log", "a", encoding="utf-8") as f:
            import datetime
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{ts}] {msg}\n")
        print(f"[RUNTIME] {msg}")
    except:
        print(msg)

def _sanitize(name: str) -> str:
    return re.sub(r"[^\w\-.]+", "_", name)

try:
    import openvino as ov
    _core = ov.Core()
    AVAILABLE_DEVICES = ["AUTO"] + list(_core.available_devices)
    log_to_file(f"OpenVINO Core init success. Devices: {AVAILABLE_DEVICES}")
except Exception as e:
    log_to_file(f"WARN: OpenVINO Core init failed: {e}")
    AVAILABLE_DEVICES = ["AUTO", "CPU", "GPU", "NPU"]

class RuntimeState:
    def __init__(self) -> None:
        self.model_source: str = "local"
        self.model_id: str = ""
        self.model_dir: Optional[str] = None
        self.device: str = "AUTO"
        self.tokenizer: Optional[ov_genai.Tokenizer] = None
        self.pipe: Optional[ov_genai.LLMPipeline] = None
        self.model_path: Optional[Path] = None

    def unload(self):
        """安全卸载模型，防止显存残留导致闪退"""
        log_to_file("Unloading model...")
        
        if self.pipe is not None:
            try: del self.pipe
            except: pass
        if self.tokenizer is not None:
            try: del self.tokenizer
            except: pass
            
        self.pipe = None
        self.tokenizer = None
        
        gc.collect()
        gc.collect()
        
        time.sleep(0.5)
        log_to_file("Model unloaded and memory cleared.")

    def _load_local(self, path: Path) -> Path:
        if not path.exists():
            raise RuntimeError(f"本地模型目录不存在: {path}")
        return path

    def ensure_loaded(
        self,
        model_source: Optional[str] = None,
        model_id: Optional[str] = None,
        model_dir: Optional[str] = None,
        device: Optional[str] = None,
    ) -> Tuple[str, str]:
        
        want_source = model_source or self.model_source
        want_id     = model_id or self.model_id
        want_dir    = model_dir or self.model_dir
        want_device = device or self.device

        log_to_file(f"Request load: dir={want_dir}, device={want_device}")

        need_reload = (
            (want_source != self.model_source) or
            ((want_dir or None) != (self.model_dir or None)) or
            (want_device != self.device) or
            (self.pipe is None)
        )
        
        if not need_reload and self.pipe:
            log_to_file("Pipeline reusing existing instance.")
            return (str(self.model_path), self.device)

        self.unload()

        if want_source == "local":
            model_path = self._load_local(Path(want_dir).resolve())
        else:
            raise RuntimeError(f"只支持 local 模式")

        str_path = str(model_path)
        log_to_file(f"Initializing Tokenizer from {str_path}...")
        
        try:
            tok = ov_genai.Tokenizer(str_path)
        except Exception as e:
            log_to_file(f"FATAL: Tokenizer init failed: {e}")
            raise e
        
        dev = want_device if want_device in AVAILABLE_DEVICES else "AUTO"
        
        log_to_file(f"Initializing LLMPipeline on {dev}...")
        try:
            pipe = ov_genai.LLMPipeline(str_path, device=dev)
            log_to_file("LLMPipeline created successfully.")
        except Exception as e:
            log_to_file(f"ERROR: Pipeline init failed on {dev}: {e}")
            log_to_file("Attempting fallback to CPU...")
            dev = "CPU"
            pipe = ov_genai.LLMPipeline(str_path, device=dev)
            log_to_file("Fallback to CPU successful.")

        self.model_source = want_source
        self.model_id = want_id
        self.model_dir = str(model_path)
        self.device = dev
        self.model_path = model_path
        self.tokenizer = tok
        self.pipe = pipe
        
        return (str(self.model_path), self.device)