import gc
import os
import re
import time
import sys
from pathlib import Path
from typing import Optional, Tuple, Callable, Any, TYPE_CHECKING
from app.config import MODELS_DIR, OV_CACHE_DIR, LOGS_DIR

if TYPE_CHECKING:
    import openvino_genai as ov_genai

LOG_PATH = LOGS_DIR / "runtime.log"

def log_to_file(msg):
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            import datetime
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{ts}][pid {os.getpid()}] {msg}\n")
        print(f"[RUNTIME] {msg}")
    except Exception:
        print(msg)

def _sanitize(name: str) -> str:
    return re.sub(r"[^\w\-.]+", "_", name)

try:
    import openvino as ov
    _core = ov.Core()
    AVAILABLE_DEVICES = ["AUTO"] + list(_core.available_devices)
    CACHE_SUPPORTED_DEVICES = set()
    for dev in _core.available_devices:
        try:
            props = _core.get_property(dev, "SUPPORTED_PROPERTIES")
        except Exception:
            continue
        if "CACHE_DIR" in props:
            CACHE_SUPPORTED_DEVICES.add(dev)
    log_to_file(f"OpenVINO Core init success. Devices: {AVAILABLE_DEVICES}")
except Exception as e:
    log_to_file(f"WARN: OpenVINO Core init failed: {e}")
    AVAILABLE_DEVICES = ["AUTO", "CPU", "GPU", "NPU"]
    CACHE_SUPPORTED_DEVICES = set()

def _parse_bool_env(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    value = value.strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    return None

def _build_device_props(dev: str, model_path: Path) -> dict:
    props = {}

    if dev in CACHE_SUPPORTED_DEVICES:
        cache_root = os.environ.get("IDLE_NPU_OV_CACHE_DIR")
        cache_root_path = Path(cache_root) if cache_root else OV_CACHE_DIR
        cache_dir = cache_root_path / _sanitize(f"{model_path.name}-{dev}")
        cache_dir.mkdir(parents=True, exist_ok=True)
        props["CACHE_DIR"] = str(cache_dir)

    if dev == "NPU":
        defer_weights = _parse_bool_env(os.environ.get("IDLE_NPU_DEFER_WEIGHTS_LOAD"))
        if defer_weights is not None:
            props["NPU_DEFER_WEIGHTS_LOAD"] = defer_weights

        comp_threads = os.environ.get("IDLE_NPU_COMPILATION_NUM_THREADS")
        if comp_threads:
            try:
                props["COMPILATION_NUM_THREADS"] = int(comp_threads)
            except ValueError:
                pass

    return props

class RuntimeState:
    def __init__(self) -> None:
        self.model_source: str = "local"
        self.model_id: str = ""
        self.model_dir: Optional[str] = None
        self.device: str = "AUTO"
        self.tokenizer: Optional[Any] = None
        self.pipe: Optional[Any] = None
        self.model_path: Optional[Path] = None
        self.model_kind: str = "llm"
        self._ov_genai: Optional[Any] = None

    def _get_ov_genai(self):
        if self._ov_genai is None:
            import openvino_genai as ov_genai
            self._ov_genai = ov_genai
        return self._ov_genai

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
        self.model_kind = "llm"
        
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
        max_prompt_len: int = 16384,
        progress_cb: Optional[Callable[[str, str], None]] = None,
    ) -> Tuple[str, str, str]:

        want_source = model_source or self.model_source
        want_id     = model_id or self.model_id
        want_dir    = model_dir or self.model_dir
        want_device = device or self.device

        log_to_file(f"Request load: dir={want_dir}, device={want_device}")
        if progress_cb:
            progress_cb("start", f"Loading {want_dir or ''}")

        need_reload = (
            (want_source != self.model_source) or
            ((want_dir or None) != (self.model_dir or None)) or
            (want_device != self.device) or
            (self.pipe is None)
        )
        
        if not need_reload and self.pipe:
            log_to_file("Pipeline reusing existing instance.")
            return (str(self.model_path), self.device, self.model_kind)

        self.unload()

        if want_source == "local":
            model_path = self._load_local(Path(want_dir).resolve())
        else:
            raise RuntimeError(f"只支持 local 模式")

        str_path = str(model_path)
        try:
            from app.utils.model_type import detect_model_kind
            model_kind = detect_model_kind(model_path)
        except Exception:
            model_kind = "llm"
        log_to_file(f"Detected model type: {model_kind}")
        log_to_file(f"Initializing Tokenizer from {str_path}...")
        if progress_cb:
            progress_cb("tokenizer", "Initializing tokenizer")
        
        try:
            ov_genai = self._get_ov_genai()
            tok = ov_genai.Tokenizer(str_path)
        except Exception as e:
            log_to_file(f"FATAL: Tokenizer init failed: {e}")
            raise e
        
        dev = want_device if want_device in AVAILABLE_DEVICES else "AUTO"
        device_props = _build_device_props(dev, model_path)
        if device_props:
            log_to_file(f"Device properties: {device_props}")

        pipeline_name = "VLMPipeline" if model_kind == "vlm" else "LLMPipeline"
        log_to_file(f"Initializing {pipeline_name} on {dev}...")
        if progress_cb:
            progress_cb("pipeline", f"Initializing pipeline on {dev}")
        try:
            if model_kind == "vlm":
                try:
                    if dev == "NPU" or (dev == "AUTO" and "NPU" in AVAILABLE_DEVICES):
                        pipe = ov_genai.VLMPipeline(
                            str_path, device=dev, MAX_PROMPT_LEN=max_prompt_len, **device_props
                        )
                        log_to_file(f"VLMPipeline created with MAX_PROMPT_LEN={max_prompt_len}")
                    else:
                        pipe = ov_genai.VLMPipeline(str_path, device=dev, **device_props)
                        log_to_file("VLMPipeline created successfully.")
                except TypeError:
                    pipe = ov_genai.VLMPipeline(str_path, device=dev, **device_props)
                    log_to_file("VLMPipeline created successfully.")
            else:
                # NPU needs MAX_PROMPT_LEN for longer conversations
                if dev == "NPU" or (dev == "AUTO" and "NPU" in AVAILABLE_DEVICES):
                    pipe = ov_genai.LLMPipeline(
                        str_path, device=dev, MAX_PROMPT_LEN=max_prompt_len, **device_props
                    )
                    log_to_file(f"LLMPipeline created with MAX_PROMPT_LEN={max_prompt_len}")
                else:
                    pipe = ov_genai.LLMPipeline(str_path, device=dev, **device_props)
                    log_to_file("LLMPipeline created successfully.")
        except Exception as e:
            log_to_file(f"ERROR: Pipeline init failed on {dev}: {e}")
            log_to_file("Attempting fallback to CPU...")
            dev = "CPU"
            if progress_cb:
                progress_cb("fallback", "Falling back to CPU")
            device_props = _build_device_props(dev, model_path)
            if model_kind == "vlm":
                pipe = ov_genai.VLMPipeline(str_path, device=dev, **device_props)
            else:
                pipe = ov_genai.LLMPipeline(str_path, device=dev, **device_props)
            log_to_file("Fallback to CPU successful.")

        self.model_source = want_source
        self.model_id = want_id
        self.model_dir = str(model_path)
        self.device = dev
        self.model_path = model_path
        self.model_kind = model_kind
        self.tokenizer = tok
        self.pipe = pipe

        if progress_cb:
            progress_cb("ready", "Model ready")
        
        return (str(self.model_path), self.device, self.model_kind)
