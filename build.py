import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

APP_NAME = "IdleNPUWaker" 

MAIN_SCRIPT = "main.py"

ICON_FILE = "app.ico"

COLLECT_PACKAGES = [
    "openvino_genai",
    "openvino",
    "openvino_tokenizers",
    "modelscope",
    "markdown"
]

ADD_DATA = [
    "app;app",
    "app/lang;app/lang"
]

def print_step(msg):
    print(f"\n{'='*60}\n[BUILD] {msg}\n{'='*60}")

def clean_build_dirs():
    """清理之前的构建文件，防止缓存干扰"""
    print_step("正在清理旧构建文件...")
    dirs_to_remove = ["build", "dist"]
    files_to_remove = [f"{APP_NAME}.spec", "Intel_NPU_AI_Boost.spec"]
    
    for d in dirs_to_remove:
        if os.path.exists(d):
            try:
                shutil.rmtree(d)
                print(f" - 已删除目录: {d}")
            except Exception as e:
                print(f" ! 无法删除目录 {d}: {e}")
    
    for f in files_to_remove:
        if os.path.exists(f):
            try:
                os.remove(f)
                print(f" - 已删除文件: {f}")
            except Exception as e:
                print(f" ! 无法删除文件 {f}: {e}")

def run_pyinstaller():
    """构建并执行 PyInstaller 命令"""
    print_step("准备打包命令...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        f"--name={APP_NAME}",
        MAIN_SCRIPT
    ]

    if os.path.exists(ICON_FILE):
        cmd.insert(4, f"--icon={ICON_FILE}")
        print(f" - 发现图标: {ICON_FILE}")
    else:
        print(f" ! 未找到图标 {ICON_FILE}，将使用默认图标")

    for data in ADD_DATA:
        cmd.append(f"--add-data={data}")

    for pkg in COLLECT_PACKAGES:
        cmd.append(f"--collect-all={pkg}")

    print("执行命令:\n" + " ".join(cmd))
    
    print_step("开始打包 (这也可能需要几分钟，请耐心等待)...")
    
    start_time = time.time()
    result = subprocess.run(cmd)
    end_time = time.time()
    
    if result.returncode == 0:
        duration = end_time - start_time
        print_step(f"打包成功！耗时: {duration:.2f} 秒")
        return True
    else:
        print_step("打包失败，请检查上方错误信息。")
        return False

def main():
    clean_build_dirs()
    
    success = run_pyinstaller()
    
    if success:
        dist_path = Path("dist").resolve()
        exe_path = dist_path / f"{APP_NAME}.exe" if os.name == 'nt' else dist_path / APP_NAME
        
        print(f"\n你的程序位于:\n -> {exe_path}\n")
        
        if os.name == 'nt':
            try:
                time.sleep(2)
                os.startfile(dist_path)
            except:
                pass

if __name__ == "__main__":
    main()