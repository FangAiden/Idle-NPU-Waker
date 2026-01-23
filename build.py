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

COLLECT_PACKAGES = [
    "openvino_genai",
    "openvino",
    "openvino_tokenizers",
    "modelscope",
]

ADD_DATA = [
    "app;app",
    "frontend;frontend",
]


def print_step(message: str) -> None:
    bar = "=" * 60
    print(f"\n{bar}\n[BUILD] {message}\n{bar}")


def run_command(cmd: list[str], cwd: Path | None = None) -> bool:
    print("Command:\n" + " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    return result.returncode == 0


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


def build_backend_exe() -> bool:
    print_step("Building backend EXE (PyInstaller)")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        f"--name={APP_NAME}",
        MAIN_SCRIPT,
    ]
    if (ROOT_DIR / ICON_FILE).exists():
        cmd.insert(4, f"--icon={ICON_FILE}")

    for data in ADD_DATA:
        cmd.append(f"--add-data={data}")
    for pkg in COLLECT_PACKAGES:
        cmd.append(f"--collect-all={pkg}")

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
    parser.add_argument("--clean", action="store_true", help="Clean build/dist before building.")
    args = parser.parse_args()

    if args.clean:
        clean_build_dirs()

    if not args.skip_backend:
        if should_rebuild_backend(args.force_backend):
            if not build_backend_exe():
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
