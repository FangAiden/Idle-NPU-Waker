import gc
import json
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

def _build_device_props(dev: str, model_path: Path, cache_tag: Optional[str] = None,
                        disable_cache: bool = False) -> dict:
    props = {}

    if not disable_cache and dev in CACHE_SUPPORTED_DEVICES:
        cache_root = os.environ.get("IDLE_NPU_OV_CACHE_DIR")
        cache_root_path = Path(cache_root) if cache_root else OV_CACHE_DIR
        cache_name = f"{model_path.name}-{dev}"
        if cache_tag:
            cache_name = f"{cache_name}-{cache_tag}"
        cache_dir = cache_root_path / _sanitize(cache_name)
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

def _image_cache_tag(max_sequence_length: Optional[int]) -> str:
    if isinstance(max_sequence_length, int) and max_sequence_length > 0:
        return f"imgseq{max_sequence_length}"
    return "imgseqauto"

def _is_flux_model(model_path: Path) -> bool:
    cfg_path = model_path / "transformer" / "config.json"
    if not cfg_path.exists():
        return False
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    class_name = data.get("_class_name") or data.get("model_type")
    return str(class_name).strip().lower() == "fluxtransformer2dmodel"

def _build_flux_pipeline(ov_genai, model_path: Path, dev: str, device_props: dict,
                         max_sequence_length: Optional[int]) -> Any:
    scheduler_path = model_path / "scheduler" / "scheduler_config.json"
    if not scheduler_path.exists():
        raise RuntimeError("Missing scheduler_config.json for FLUX pipeline.")
    scheduler = ov_genai.Scheduler.from_config(str(scheduler_path), ov_genai.Scheduler.Type.AUTO)

    clip_path = model_path / "text_encoder"
    t5_path = model_path / "text_encoder_2"
    transformer_path = model_path / "transformer"
    vae_encoder_path = model_path / "vae_encoder"
    vae_decoder_path = model_path / "vae_decoder"

    clip = ov_genai.CLIPTextModel(str(clip_path))
    t5 = ov_genai.T5EncoderModel(str(t5_path))
    transformer = ov_genai.FluxTransformer2DModel(str(transformer_path))
    vae = ov_genai.AutoencoderKL(str(vae_encoder_path), str(vae_decoder_path))

    if isinstance(max_sequence_length, int) and max_sequence_length > 0:
        t5.reshape(1, int(max_sequence_length))

    clip.compile(dev, **device_props)
    t5.compile(dev, **device_props)
    transformer.compile(dev, **device_props)
    vae.compile(dev, **device_props)

    return ov_genai.Text2ImagePipeline.flux(scheduler, clip, t5, transformer, vae)

def _infer_image_supported_keys() -> Optional[set]:
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
        return keys or None
    except Exception:
        return None

def _infer_asr_supported_keys() -> Optional[set]:
    try:
        import openvino_genai as ov_genai
        cfg = ov_genai.WhisperGenerationConfig()
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
        return keys or None
    except Exception:
        return None

def _infer_image_max_sequence_length(model_path: Path) -> Optional[int]:
    candidates = [
        model_path / "tokenizer_2" / "tokenizer_config.json",
        model_path / "tokenizer" / "tokenizer_config.json",
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
        self.max_prompt_len: Optional[int] = None
        self.supported_keys: Optional[set] = None
        self.image_max_sequence_length: Optional[int] = None

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
        self.max_prompt_len = None
        self.supported_keys = None
        self.image_max_sequence_length = None
        
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
        image_max_sequence_length: Optional[int] = None,
        cache_bust: Optional[str] = None,
        progress_cb: Optional[Callable[[str, str], None]] = None,
    ) -> Tuple[str, str, str]:

        want_source = model_source or self.model_source
        want_id     = model_id or self.model_id
        want_dir    = model_dir or self.model_dir
        want_device = device or self.device
        want_image_seq = image_max_sequence_length if isinstance(image_max_sequence_length, int) and image_max_sequence_length > 0 else None

        log_to_file(f"Request load: dir={want_dir}, device={want_device}")
        if progress_cb:
            progress_cb("start", f"Loading {want_dir or ''}")

        need_reload = (
            (want_source != self.model_source) or
            ((want_dir or None) != (self.model_dir or None)) or
            (want_device != self.device) or
            (self.pipe is None) or
            (want_image_seq is not None and self.model_kind == "image" and want_image_seq != self.image_max_sequence_length) or
            (cache_bust is not None)
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
        image_max_seq = None
        image_cache_tag = None
        is_flux = False
        if model_kind == "image":
            if isinstance(image_max_sequence_length, int) and image_max_sequence_length > 0:
                image_max_seq = image_max_sequence_length
            else:
                image_max_seq = _infer_image_max_sequence_length(model_path)
            image_cache_tag = _image_cache_tag(image_max_seq)
            if cache_bust:
                image_cache_tag = f"{image_cache_tag}-{cache_bust}"
            is_flux = _is_flux_model(model_path)
        tok = None
        ov_genai = self._get_ov_genai()
        if model_kind in ("llm", "vlm"):
            log_to_file(f"Initializing Tokenizer from {str_path}...")
            if progress_cb:
                progress_cb("tokenizer", "Initializing tokenizer")
            try:
                tok = ov_genai.Tokenizer(str_path)
            except Exception as e:
                log_to_file(f"FATAL: Tokenizer init failed: {e}")
                raise e
        else:
            log_to_file("Skipping tokenizer for non-LLM model.")
        
        dev = want_device if want_device in AVAILABLE_DEVICES else "AUTO"
        device_props = _build_device_props(dev, model_path, cache_tag=image_cache_tag,
                                           disable_cache=is_flux if model_kind == "image" else False)
        if device_props:
            log_to_file(f"Device properties: {device_props}")

        if model_kind == "image":
            pipeline_name = "Text2ImagePipeline"
        elif model_kind == "asr":
            pipeline_name = "WhisperPipeline"
        else:
            pipeline_name = "VLMPipeline" if model_kind == "vlm" else "LLMPipeline"
        log_to_file(f"Initializing {pipeline_name} on {dev}...")
        if progress_cb:
            progress_cb("pipeline", f"Initializing pipeline on {dev}")
        try:
            if model_kind == "image":
                if is_flux:
                    log_to_file("Detected FLUX pipeline. Building components manually.")
                    pipe = _build_flux_pipeline(ov_genai, model_path, dev, device_props, image_max_seq)
                else:
                    try:
                        pipe = ov_genai.Text2ImagePipeline(str_path, device=dev, **device_props)
                    except TypeError:
                        pipe = ov_genai.Text2ImagePipeline(str_path, dev)
                self.max_prompt_len = None
                self.supported_keys = _infer_image_supported_keys()
                self.image_max_sequence_length = image_max_seq
                if self.image_max_sequence_length:
                    try:
                        cfg = pipe.get_generation_config()
                        if hasattr(cfg, "max_sequence_length"):
                            cfg.max_sequence_length = int(self.image_max_sequence_length)
                            pipe.set_generation_config(cfg)
                            log_to_file(f"Text2ImagePipeline max_sequence_length set to {self.image_max_sequence_length}")
                    except Exception as e:
                        log_to_file(f"WARN: Failed to set max_sequence_length for image pipeline: {e}")
                log_to_file("Text2ImagePipeline created successfully.")
            elif model_kind == "asr":
                pipe = ov_genai.WhisperPipeline(str_path, device=dev, **device_props)
                self.max_prompt_len = None
                self.supported_keys = _infer_asr_supported_keys()
                log_to_file("WhisperPipeline created successfully.")
            elif model_kind == "vlm":
                self.supported_keys = None
                if dev == "NPU" or (dev == "AUTO" and "NPU" in AVAILABLE_DEVICES):
                    try:
                        pipe = ov_genai.VLMPipeline(
                            str_path, device=dev, MAX_PROMPT_LEN=max_prompt_len, **device_props
                        )
                        self.max_prompt_len = max_prompt_len
                        log_to_file(f"VLMPipeline created with MAX_PROMPT_LEN={max_prompt_len}")
                    except Exception as e:
                        log_to_file(f"WARN: VLMPipeline MAX_PROMPT_LEN unsupported, retry without it: {e}")
                        pipe = ov_genai.VLMPipeline(str_path, device=dev, **device_props)
                        self.max_prompt_len = 1024
                        log_to_file("VLMPipeline created successfully.")
                else:
                    pipe = ov_genai.VLMPipeline(str_path, device=dev, **device_props)
                    self.max_prompt_len = max_prompt_len
                    log_to_file("VLMPipeline created successfully.")
            else:
                # NPU needs MAX_PROMPT_LEN for longer conversations
                self.supported_keys = None
                if dev == "NPU" or (dev == "AUTO" and "NPU" in AVAILABLE_DEVICES):
                    try:
                        pipe = ov_genai.LLMPipeline(
                            str_path, device=dev, MAX_PROMPT_LEN=max_prompt_len, **device_props
                        )
                        self.max_prompt_len = max_prompt_len
                        log_to_file(f"LLMPipeline created with MAX_PROMPT_LEN={max_prompt_len}")
                    except Exception as e:
                        log_to_file(f"WARN: MAX_PROMPT_LEN unsupported, retry without it: {e}")
                        pipe = ov_genai.LLMPipeline(str_path, device=dev, **device_props)
                        self.max_prompt_len = max_prompt_len
                        log_to_file("LLMPipeline created successfully.")
                else:
                    pipe = ov_genai.LLMPipeline(str_path, device=dev, **device_props)
                    self.max_prompt_len = max_prompt_len
                    log_to_file("LLMPipeline created successfully.")
        except Exception as e:
            log_to_file(f"ERROR: Pipeline init failed on {dev}: {e}")
            log_to_file("Attempting fallback to CPU...")
            dev = "CPU"
            if progress_cb:
                progress_cb("fallback", "Falling back to CPU")
            device_props = _build_device_props(dev, model_path, cache_tag=image_cache_tag,
                                               disable_cache=is_flux if model_kind == "image" else False)
            if model_kind == "image":
                if is_flux:
                    log_to_file("Detected FLUX pipeline. Building components manually.")
                    pipe = _build_flux_pipeline(ov_genai, model_path, dev, device_props, image_max_seq)
                else:
                    try:
                        pipe = ov_genai.Text2ImagePipeline(str_path, device=dev, **device_props)
                    except TypeError:
                        pipe = ov_genai.Text2ImagePipeline(str_path, dev)
                self.max_prompt_len = None
                self.supported_keys = _infer_image_supported_keys()
                self.image_max_sequence_length = image_max_seq
                if self.image_max_sequence_length:
                    try:
                        cfg = pipe.get_generation_config()
                        if hasattr(cfg, "max_sequence_length"):
                            cfg.max_sequence_length = int(self.image_max_sequence_length)
                            pipe.set_generation_config(cfg)
                            log_to_file(f"Text2ImagePipeline max_sequence_length set to {self.image_max_sequence_length}")
                    except Exception as e:
                        log_to_file(f"WARN: Failed to set max_sequence_length for image pipeline: {e}")
            elif model_kind == "asr":
                pipe = ov_genai.WhisperPipeline(str_path, device=dev, **device_props)
                self.max_prompt_len = None
                self.supported_keys = _infer_asr_supported_keys()
            elif model_kind == "vlm":
                pipe = ov_genai.VLMPipeline(str_path, device=dev, **device_props)
                self.max_prompt_len = max_prompt_len
                self.supported_keys = None
            else:
                pipe = ov_genai.LLMPipeline(str_path, device=dev, **device_props)
                self.max_prompt_len = max_prompt_len
                self.supported_keys = None
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
