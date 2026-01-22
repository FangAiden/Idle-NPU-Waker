import os
import sys
import ctypes
from typing import Optional


def _get_memory_windows() -> dict:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    memory = MEMORYSTATUSEX()
    memory.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))

    total = int(memory.ullTotalPhys)
    available = int(memory.ullAvailPhys)
    used = max(0, total - available)
    percent = int(memory.dwMemoryLoad)

    return {
        "total": total,
        "available": available,
        "used": used,
        "percent": percent,
    }


def _get_memory_proc() -> dict:
    meminfo = {}
    with open("/proc/meminfo", "r", encoding="utf-8") as f:
        for line in f:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            parts = value.strip().split()
            if not parts:
                continue
            try:
                meminfo[key] = int(parts[0]) * 1024
            except ValueError:
                continue

    total = int(meminfo.get("MemTotal", 0))
    available = int(meminfo.get("MemAvailable", meminfo.get("MemFree", 0)))
    used = max(0, total - available)
    percent = int((used / total) * 100) if total > 0 else 0

    return {
        "total": total,
        "available": available,
        "used": used,
        "percent": percent,
    }


def get_memory_status() -> dict:
    if sys.platform.startswith("win"):
        return _get_memory_windows()
    if os.path.exists("/proc/meminfo"):
        return _get_memory_proc()
    return {"total": 0, "available": 0, "used": 0, "percent": 0}


def _get_process_memory_windows(pid: int) -> dict:
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010

    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)

    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        return {"rss": 0, "private": 0}
    try:
        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return {"rss": 0, "private": 0}
        return {
            "rss": int(counters.WorkingSetSize),
            "private": int(counters.PrivateUsage),
        }
    finally:
        kernel32.CloseHandle(handle)


def _get_process_memory_proc(pid: int) -> dict:
    status_path = f"/proc/{pid}/status"
    if not os.path.exists(status_path):
        return {"rss": 0, "private": 0}
    rss = 0
    with open(status_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        rss = int(parts[1]) * 1024
                    except ValueError:
                        rss = 0
                break
    return {"rss": rss, "private": 0}


def get_process_memory(pid: Optional[int]) -> dict:
    if not pid:
        return {"rss": 0, "private": 0}
    try:
        if sys.platform.startswith("win"):
            return _get_process_memory_windows(pid)
        if os.path.exists(f"/proc/{pid}/status"):
            return _get_process_memory_proc(pid)
    except Exception:
        return {"rss": 0, "private": 0}
    return {"rss": 0, "private": 0}
