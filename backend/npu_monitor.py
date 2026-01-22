"""
NPU Monitor Service - Attempts to read Intel NPU utilization via Windows Performance Counters
"""
import csv
import os
import subprocess
import threading
import time
from collections import deque
from typing import Dict, List, Optional


NPU_COUNTER_CANDIDATES = [
    r"\NPU Engine(*)\Utilization Percentage",
    r"\NPU Engine(*)\Running Time",
    r"\Intel(R) NPU Engine(*)\Utilization Percentage",
    r"\Intel(R) NPU Engine(*)\Running Time",
    r"\Neural Processing Unit(*)\Utilization Percentage",
    r"\Neural Processor(*)\Utilization Percentage",
    r"\AI Processor(*)\Utilization Percentage",
]
WMI_NPU_NAME_PATTERN = "NPU|Neural|AI"
GPU_ENGINE_ENGTYPE_FALLBACKS = ("Compute", "NPU", "*")


class NPUMonitor:
    def __init__(self, history_size: int = 60):
        self._history_size = history_size
        self._utilization_history: deque = deque(maxlen=history_size)
        self._current_utilization: float = 0.0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._search_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._npu_counter_path: Optional[str] = None
        self._counter_reader: Optional[str] = None
        self._available = False
        self._searching = False
        self._stop_search = False
        self._wmi_name_pattern: Optional[str] = None
        self._wmi_luid_checked = False
        self._wmi_luid_pattern: Optional[str] = None
        self._fast_timeout = self._parse_int_env("IDLE_NPU_MONITOR_FAST_TIMEOUT", 2)
        self._deep_scan = self._parse_bool_env("IDLE_NPU_MONITOR_DEEP_SCAN", True)
        self._retry_interval = self._parse_int_env("IDLE_NPU_MONITOR_RETRY_INTERVAL", 10)

    def _parse_bool_env(self, name: str, default: bool) -> bool:
        raw = os.environ.get(name)
        if raw is None:
            return default
        value = raw.strip().lower()
        if value in ("1", "true", "yes", "on"):
            return True
        if value in ("0", "false", "no", "off"):
            return False
        return default

    def _parse_int_env(self, name: str, default: int) -> int:
        raw = os.environ.get(name)
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    def _run_powershell(self, command: str, timeout: int = 10) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    def _run_cmd(self, command: str, timeout: int = 10) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["cmd", "/c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    def _read_typeperf_counter(self, path: str, timeout: int = 6) -> Optional[float]:
        result = self._run_powershell(f'typeperf "{path}" -sc 1', timeout=timeout)
        if result.returncode != 0:
            result = self._run_cmd(f'typeperf "{path}" -sc 1', timeout=timeout)
        if result.returncode != 0:
            return None
        error_markers = ("Error:", "错误", "No valid counters")
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        if any(marker in stdout for marker in error_markers) or any(marker in stderr for marker in error_markers):
            return None
        lines = [line for line in stdout.splitlines() if line.strip()]
        if len(lines) < 2:
            return None
        values = []
        for line in reversed(lines):
            try:
                row = next(csv.reader([line]))
            except Exception:
                continue
            values = []
            for item in row[1:]:
                try:
                    values.append(float(item))
                except ValueError:
                    continue
            if values:
                break
        if not values:
            return None
        lower_path = path.lower()
        if "\\gpu engine" in lower_path:
            value = max(values)
        else:
            value = sum(values) / len(values)
        return min(100.0, max(0.0, value))

    def _read_powershell_counter(self, path: str, timeout: int = 6) -> Optional[float]:
        cmd = (
            f"$s=(Get-Counter -Counter '{path}' -ErrorAction SilentlyContinue).CounterSamples;"
            "if ($s) { ($s | Measure-Object -Property CookedValue -Average).Average }"
        )
        result = self._run_powershell(cmd, timeout=timeout)
        if result.returncode != 0:
            return None
        value = result.stdout.strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def _read_wmi_gpu_engine_utilization(
        self, name_pattern: Optional[str] = None, timeout: int = 6
    ) -> Optional[float]:
        pattern = name_pattern or WMI_NPU_NAME_PATTERN
        cmd = (
            "$items = Get-CimInstance -ClassName Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine "
            "-ErrorAction SilentlyContinue | "
            f"Where-Object {{ $_.Name -match '{pattern}' }}; "
            "if ($items) { "
            "  $groups = $items | ForEach-Object { "
            "    $m = [regex]::Match($_.Name, 'engtype_([^_]+)'); "
            "    $eng = if ($m.Success) { $m.Groups[1].Value } else { 'Unknown' }; "
            "    [pscustomobject]@{ Eng = $eng; Util = [double]$_.UtilizationPercentage } "
            "  } | Group-Object -Property Eng | ForEach-Object { "
            "    ($_.Group | Measure-Object -Property Util -Sum).Sum "
            "  }; "
            "  if ($groups) { ($groups | Measure-Object -Maximum).Maximum } "
            "}"
        )
        result = self._run_powershell(cmd, timeout=timeout)
        if result.returncode != 0:
            return None
        value = result.stdout.strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def _test_typeperf_counter(self, path: str, timeout: int = 6) -> bool:
        return self._read_typeperf_counter(path, timeout=timeout) is not None

    def _test_powershell_counter(self, path: str, timeout: int = 6) -> bool:
        return self._read_powershell_counter(path, timeout=timeout) is not None

    def _format_luid_pattern(self, luid_value) -> Optional[str]:
        if not luid_value:
            return None
        try:
            if isinstance(luid_value, (bytes, bytearray)):
                hex_str = luid_value.hex()
            else:
                hex_str = str(luid_value).strip().lower()
            hex_str = hex_str.replace("0x", "")
            if len(hex_str) % 2 != 0:
                return None
            raw = bytes.fromhex(hex_str)
            if len(raw) < 8:
                raw = raw.ljust(8, b"\x00")
            elif len(raw) > 8:
                raw = raw[:8]
            lo = int.from_bytes(raw[:4], "little")
            hi = int.from_bytes(raw[4:], "little")
            return f"luid_0x{hi:08x}_0x{lo:08x}"
        except Exception:
            return None

    def _get_wmi_luid_pattern(self) -> Optional[str]:
        if self._wmi_luid_checked:
            return self._wmi_luid_pattern
        self._wmi_luid_checked = True
        try:
            import openvino as ov

            core = ov.Core()
            if "NPU" not in getattr(core, "available_devices", []):
                return None
            luid = core.get_property("NPU", "DEVICE_LUID")
            self._wmi_luid_pattern = self._format_luid_pattern(luid)
        except Exception as e:
            print(f"[NPU Monitor] Failed to read NPU LUID: {e}")
            self._wmi_luid_pattern = None
        return self._wmi_luid_pattern

    def _build_gpu_engine_luid_paths(self, luid_pattern: str) -> List[str]:
        if not luid_pattern:
            return []
        paths: List[str] = []
        for eng_type in GPU_ENGINE_ENGTYPE_FALLBACKS:
            paths.append(
                rf"\GPU Engine(pid_*_{luid_pattern}_phys_*_eng_*_engtype_{eng_type})\Utilization Percentage"
            )
        return paths

    def _find_npu_counter(self) -> Optional[str]:
        """Try to find NPU performance counter path"""
        env_path = os.environ.get("IDLE_NPU_COUNTER_PATH")
        if env_path:
            path = env_path.strip()
            if path.lower().startswith("wmi_gpu"):
                self._counter_reader = "wmi_gpu"
                pattern = None
                if ":" in path:
                    pattern = path.split(":", 1)[1].strip() or None
                self._wmi_name_pattern = pattern or WMI_NPU_NAME_PATTERN
                return path
            self._counter_reader = "typeperf"
            return path

        fast_timeout = max(1, self._fast_timeout)
        for path in NPU_COUNTER_CANDIDATES:
            if self._stop_search:
                return None
            if self._test_typeperf_counter(path, timeout=fast_timeout):
                self._counter_reader = "typeperf"
                return path
        for path in NPU_COUNTER_CANDIDATES:
            if self._stop_search:
                return None
            if self._test_powershell_counter(path, timeout=fast_timeout):
                self._counter_reader = "powershell"
                return path

        if self._stop_search:
            return None

        luid_pattern = self._get_wmi_luid_pattern()
        if luid_pattern:
            gpu_engine_paths = self._build_gpu_engine_luid_paths(luid_pattern)
            for path in gpu_engine_paths:
                if self._stop_search:
                    return None
                if self._test_typeperf_counter(path, timeout=fast_timeout):
                    self._counter_reader = "typeperf"
                    return path
            for path in gpu_engine_paths:
                if self._stop_search:
                    return None
                if self._test_powershell_counter(path, timeout=fast_timeout):
                    self._counter_reader = "powershell"
                    return path

        if luid_pattern:
            if self._read_wmi_gpu_engine_utilization(luid_pattern, timeout=fast_timeout) is not None:
                self._counter_reader = "wmi_gpu"
                self._wmi_name_pattern = luid_pattern
                return f"wmi_gpu:{luid_pattern}"

        if self._read_wmi_gpu_engine_utilization(WMI_NPU_NAME_PATTERN, timeout=fast_timeout) is not None:
            self._counter_reader = "wmi_gpu"
            self._wmi_name_pattern = WMI_NPU_NAME_PATTERN
            return "wmi_gpu"

        if not self._deep_scan:
            return None

        try:
            # Try to list all counters containing NPU or Neural
            result = self._run_powershell(
                "Get-Counter -ListSet * | Where-Object { $_.CounterSetName -match 'NPU|Neural|Compute' } | "
                "ForEach-Object { $_.Paths }",
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                # Look for utilization counter
                for line in lines:
                    line = line.strip()
                    if 'utilization' in line.lower() or 'usage' in line.lower() or 'running' in line.lower():
                        self._counter_reader = "powershell"
                        return line
                # If no utilization counter, return first one
                if lines:
                    self._counter_reader = "powershell"
                    return lines[0].strip()
        except Exception as e:
            print(f"[NPU Monitor] Failed to find counter: {e}")

        # Fallback: try GPU Engine counters (some NPUs appear here)
        try:
            result = self._run_powershell(
                r"Get-Counter -ListSet 'GPU Engine' -ErrorAction SilentlyContinue | "
                r"ForEach-Object { $_.Paths } | Select-Object -First 5",
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'npu' in line.lower() or 'neural' in line.lower():
                        self._counter_reader = "powershell"
                        return line.strip()
        except Exception:
            pass

        try:
            result = self._run_cmd(
                'typeperf -qx | findstr /I /C:"NPU" /C:"Neural" /C:"AI Processor"',
                timeout=12
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                for line in lines:
                    if "utilization" in line.lower() or "usage" in line.lower() or "running" in line.lower():
                        self._counter_reader = "typeperf"
                        return self._normalize_typeperf_path(line)
                if lines:
                    self._counter_reader = "typeperf"
                    return self._normalize_typeperf_path(lines[0])
        except Exception:
            pass

        return None

    def _normalize_typeperf_path(self, line: str) -> str:
        if line.startswith("\\\\"):
            parts = line.split("\\", 3)
            if len(parts) >= 4:
                return "\\" + parts[3]
        return line

    def _read_utilization(self) -> float:
        """Read NPU utilization percentage"""
        if not self._npu_counter_path:
            return 0.0

        try:
            if self._counter_reader == "wmi_gpu":
                value = self._read_wmi_gpu_engine_utilization(self._wmi_name_pattern)
            elif self._counter_reader == "typeperf":
                value = self._read_typeperf_counter(self._npu_counter_path)
            else:
                value = self._read_powershell_counter(self._npu_counter_path)
            if value is not None:
                return min(100.0, max(0.0, value))
        except Exception as e:
            print(f"[NPU Monitor] Read error: {e}")

        return 0.0

    def _search_loop(self):
        while not self._stop_search:
            counter_path = self._find_npu_counter()
            with self._lock:
                if self._stop_search:
                    self._searching = False
                    return
                self._npu_counter_path = counter_path
                self._available = counter_path is not None

            if counter_path:
                print(f"[NPU Monitor] Found counter: {self._npu_counter_path}")
                self._running = True
                self._searching = False
                self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
                self._thread.start()
                return

            print("[NPU Monitor] No NPU performance counter found, retrying...")
            time.sleep(max(1, self._retry_interval))

        self._searching = False

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self._running:
            util = self._read_utilization()
            with self._lock:
                self._current_utilization = util
                self._utilization_history.append({
                    "time": time.time(),
                    "value": util
                })
            time.sleep(1)  # Sample every second

    def start(self) -> bool:
        """Start NPU monitoring"""
        if self._running:
            return self._available
        if self._searching:
            return self._available

        self._stop_search = False
        self._counter_reader = None
        self._npu_counter_path = None
        self._available = False
        self._searching = True
        self._search_thread = threading.Thread(target=self._search_loop, daemon=True)
        self._search_thread.start()

        return self._available

    def stop(self):
        """Stop monitoring"""
        self._running = False
        self._stop_search = True
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        if self._search_thread:
            self._search_thread.join(timeout=2)
            self._search_thread = None
        self._searching = False

    def get_current(self) -> float:
        """Get current utilization"""
        with self._lock:
            return self._current_utilization

    def get_history(self) -> List[Dict]:
        """Get utilization history"""
        with self._lock:
            return list(self._utilization_history)

    def is_available(self) -> bool:
        """Check if NPU monitoring is available"""
        return self._available

    def is_searching(self) -> bool:
        """Check if NPU monitor is still searching for counters"""
        return self._searching


# Singleton instance
_monitor: Optional[NPUMonitor] = None


def get_npu_monitor() -> NPUMonitor:
    global _monitor
    if _monitor is None:
        _monitor = NPUMonitor()
    return _monitor
