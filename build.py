import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

APP_NAME = "IdleNPUWaker"
MAIN_SCRIPT = "main.py"
ICON_FILE = "app.ico"

ROOT_DIR = Path(__file__).resolve().parent
DIST_DIR = ROOT_DIR / "dist"
TAURI_DIR = ROOT_DIR / "src-tauri"
TAURI_BIN_DIR = TAURI_DIR / "bin"
TAURI_TARGET_DIR = TAURI_DIR / "target" / "release" / "bundle"
BUILD_VENV_DIR = ROOT_DIR / ".venv-build"
REQ_HASH_FILE = BUILD_VENV_DIR / "requirements.sha256"

COLLECT_ALL_PACKAGES = [
    "openvino_genai",
    "openvino",
    "openvino_tokenizers",
    "modelscope",
]

COLLECT_BINARIES = [
    "openvino",
    "openvino_genai",
    "openvino_tokenizers",
]

COLLECT_SUBMODULES = [
    "openvino",
    "openvino_genai",
    "openvino_tokenizers",
    "modelscope",
]

COLLECT_DATA = [
    "openvino",
]

ADD_DATA = [
    "app;app",
    "frontend;frontend",
]

SLIM_EXCLUDES = [
    "torch",
    "torchvision",
    "torchaudio",
    "triton",
    "tensorflow",
    "jax",
    "jaxlib",
    "cupy",
    "xformers",
    "bitsandbytes",
]


def print_step(message: str) -> None:
    bar = "=" * 60
    print(f"\n{bar}\n[BUILD] {message}\n{bar}")


def run_command(cmd: list[str], cwd: Path | None = None) -> bool:
    print("Command:\n" + " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    return result.returncode == 0


def sha256_file(path: Path) -> str:
    import hashlib

    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def latest_mtime(paths: list[Path]) -> float:
    latest = 0.0
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            latest = max(latest, path.stat().st_mtime)
            continue
        for file in path.rglob("*"):
            if file.is_file():
                latest = max(latest, file.stat().st_mtime)
    return latest


def is_output_stale(output: Path, inputs: list[Path]) -> bool:
    if not output.exists():
        return True
    return output.stat().st_mtime < latest_mtime(inputs)


def find_tauri_outputs() -> list[Path]:
    if not TAURI_TARGET_DIR.exists():
        return []
    outputs: list[Path] = []
    for suffix in (".msi", ".exe", ".dmg", ".app", ".deb", ".rpm"):
        outputs.extend(TAURI_TARGET_DIR.rglob(f"*{suffix}"))
    return outputs


def detect_target_triple() -> str:
    env_triple = os.environ.get("TAURI_TARGET_TRIPLE") or os.environ.get("TARGET")
    if env_triple:
        return env_triple
    try:
        output = subprocess.check_output(["rustc", "-vV"], text=True)
    except (OSError, subprocess.CalledProcessError):
        output = ""
    for line in output.splitlines():
        if line.startswith("host:"):
            return line.split(":", 1)[1].strip()
    if sys.platform.startswith("win"):
        return "x86_64-pc-windows-msvc"
    if sys.platform == "darwin":
        return "aarch64-apple-darwin"
    return "x86_64-unknown-linux-gnu"


def get_tauri_cli_major() -> int | None:
    try:
        output = subprocess.check_output(["cargo", "tauri", "-V"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    for token in output.split():
        if token[0].isdigit():
            try:
                return int(token.split(".")[0])
            except ValueError:
                return None
    return None


def clean_build_dirs() -> None:
    print_step("Cleaning previous build output")
    for name in ("build", "dist"):
        path = ROOT_DIR / name
        if path.exists():
            shutil.rmtree(path)
    for name in (f"{APP_NAME}.spec", "Intel_NPU_AI_Boost.spec"):
        path = ROOT_DIR / name
        if path.exists():
            path.unlink()


def get_venv_python(venv_dir: Path) -> Path:
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def ensure_build_venv(force: bool = False) -> Path | None:
    print_step("Preparing build venv")
    base_python = os.environ.get("IDLE_NPU_BUILD_PYTHON") or sys.executable
    venv_python = get_venv_python(BUILD_VENV_DIR)

    if force and BUILD_VENV_DIR.exists():
        shutil.rmtree(BUILD_VENV_DIR)

    if not venv_python.exists():
        if not run_command([base_python, "-m", "venv", str(BUILD_VENV_DIR)]):
            return None

    req_hash = sha256_file(ROOT_DIR / "requirements.txt")
    needs_install = True
    if REQ_HASH_FILE.exists():
        try:
            needs_install = REQ_HASH_FILE.read_text(encoding="utf-8").strip() != req_hash
        except OSError:
            needs_install = True

    if needs_install:
        if not run_command([str(venv_python), "-m", "pip", "install", "-U", "pip"]):
            return None
        if not run_command([str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"]):
            return None
        if not run_command([str(venv_python), "-m", "pip", "install", "pyinstaller"]):
            return None
        REQ_HASH_FILE.write_text(req_hash, encoding="utf-8")

    return venv_python


def build_backend_exe(
    collect_all: bool,
    python_exe: Path,
    upx_dir: str | None,
    slim: bool,
) -> bool:
    print_step("Building backend EXE (PyInstaller)")
    cmd = [
        str(python_exe),
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        f"--name={APP_NAME}",
        MAIN_SCRIPT,
    ]
    if (ROOT_DIR / ICON_FILE).exists():
        cmd.insert(4, f"--icon={ICON_FILE}")
    if upx_dir:
        cmd.append(f"--upx-dir={upx_dir}")

    for data in ADD_DATA:
        cmd.append(f"--add-data={data}")
    if collect_all:
        for pkg in COLLECT_ALL_PACKAGES:
            cmd.append(f"--collect-all={pkg}")
    else:
        for pkg in COLLECT_BINARIES:
            cmd.append(f"--collect-binaries={pkg}")
        for pkg in COLLECT_SUBMODULES:
            cmd.append(f"--collect-submodules={pkg}")
        for pkg in COLLECT_DATA:
            cmd.append(f"--collect-data={pkg}")
    if slim:
        for mod in SLIM_EXCLUDES:
            cmd.append(f"--exclude-module={mod}")

    start = time.time()
    ok = run_command(cmd)
    duration = time.time() - start
    if ok:
        print_step(f"Backend EXE built in {duration:.1f}s")
    else:
        print_step("Backend EXE build failed")
    return ok


def stage_tauri_sidecar(force: bool = False) -> Path | None:
    exe_name = f"{APP_NAME}.exe" if sys.platform.startswith("win") else APP_NAME
    source = DIST_DIR / exe_name
    if not source.exists():
        print_step(f"Missing EXE: {source}")
        return None

    TAURI_BIN_DIR.mkdir(parents=True, exist_ok=True)
    target = TAURI_BIN_DIR / exe_name
    if not force and target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
        print_step(f"Sidecar up to date: {target}")
    else:
        shutil.copy2(source, target)
        print_step(f"Sidecar staged: {target}")

    triple = detect_target_triple()
    if sys.platform.startswith("win"):
        triple_name = f"{APP_NAME}-{triple}.exe"
    else:
        triple_name = f"{APP_NAME}-{triple}"
    triple_target = TAURI_BIN_DIR / triple_name
    if force or not triple_target.exists() or triple_target.stat().st_mtime < source.stat().st_mtime:
        shutil.copy2(source, triple_target)
        print_step(f"Sidecar staged: {triple_target}")

    return target


def build_tauri_app() -> bool:
    print_step("Building Tauri app")
    if not TAURI_DIR.exists():
        print_step("Missing src-tauri. Did you initialize the Tauri project?")
        return False
    major = get_tauri_cli_major()
    if major is None:
        print_step("Unable to detect tauri-cli version. Make sure cargo tauri is installed.")
        return False
    if major != 2:
        print_step("tauri-cli 2.x is required. Install with: cargo install tauri-cli")
        return False
    return run_command(["cargo", "tauri", "build"], cwd=TAURI_DIR)


def should_rebuild_backend(force: bool) -> bool:
    if force:
        return True
    exe_name = f"{APP_NAME}.exe" if sys.platform.startswith("win") else APP_NAME
    output = DIST_DIR / exe_name
    inputs = [
        ROOT_DIR / "main.py",
        ROOT_DIR / "backend",
        ROOT_DIR / "app",
        ROOT_DIR / "frontend",
        ROOT_DIR / "requirements.txt",
    ]
    return is_output_stale(output, inputs)


def should_rebuild_tauri(force: bool) -> bool:
    if force:
        return True
    outputs = find_tauri_outputs()
    if not outputs:
        return True
    exe_name = f"{APP_NAME}.exe" if sys.platform.startswith("win") else APP_NAME
    inputs = [
        TAURI_DIR / "src",
        TAURI_DIR / "tauri.conf.json",
        TAURI_DIR / "Cargo.toml",
        TAURI_DIR / "build.rs",
        TAURI_DIR / "capabilities",
        TAURI_DIR / "permissions",
        TAURI_BIN_DIR / exe_name,
    ]
    output_mtime = max((p.stat().st_mtime for p in outputs if p.exists()), default=0.0)
    return output_mtime < latest_mtime(inputs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build backend EXE and Tauri bundle.")
    parser.add_argument("--skip-backend", action="store_true", help="Skip PyInstaller step.")
    parser.add_argument("--skip-tauri", action="store_true", help="Skip Tauri bundling.")
    parser.add_argument("--force-backend", action="store_true", help="Force PyInstaller rebuild.")
    parser.add_argument("--force-tauri", action="store_true", help="Force Tauri rebuild.")
    parser.add_argument("--no-venv", action="store_true", help="Build with current interpreter instead of a clean venv.")
    parser.add_argument("--force-venv", action="store_true", help="Recreate the build venv.")
    parser.add_argument("--upx-dir", help="Optional UPX directory for PyInstaller compression.")
    parser.add_argument(
        "--slim",
        action="store_true",
        help="Exclude large optional ML packages (torch, triton, transformers, scipy, etc.).",
    )
    parser.add_argument(
        "--collect-all",
        action="store_true",
        help="Use PyInstaller --collect-all for OpenVINO/ModelScope packages (larger size).",
    )
    parser.add_argument("--clean", action="store_true", help="Clean build/dist before building.")
    args = parser.parse_args()

    if args.clean:
        clean_build_dirs()

    if not args.skip_backend:
        python_exe = Path(sys.executable)
        if not args.no_venv:
            venv_python = ensure_build_venv(force=args.force_venv)
            if not venv_python:
                sys.exit(1)
            python_exe = venv_python

        upx_dir = args.upx_dir or os.environ.get("IDLE_NPU_UPX_DIR")
        if upx_dir and not Path(upx_dir).exists():
            print_step(f"UPX dir not found: {upx_dir}")
            upx_dir = None

        if should_rebuild_backend(args.force_backend):
            if not build_backend_exe(args.collect_all, python_exe, upx_dir, args.slim):
                sys.exit(1)
        else:
            print_step("Backend EXE is up to date")

    if not args.skip_tauri:
        if not stage_tauri_sidecar(force=args.force_backend):
            sys.exit(1)

        if should_rebuild_tauri(args.force_tauri):
            if not build_tauri_app():
                sys.exit(1)
        else:
            print_step("Tauri bundle is up to date")

    print_step("Build completed")


if __name__ == "__main__":
    main()
