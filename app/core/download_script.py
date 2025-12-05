import sys
import os
import shutil
import re
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

PATTERN_PROGRESS = re.compile(r"Downloading \[(.+?)\]:\s*(\d+)%")
PATTERN_ANSI = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class StreamAdapter:
    def write(self, text):
        if not text: return
        try:
            matches = PATTERN_PROGRESS.findall(text)
            for filename, percent in matches:
                print(f"@PROGRESS@{filename}@{percent}")
                sys.stdout.flush()
        except: pass
        
        clean_text = PATTERN_ANSI.sub('', text).strip()
        if clean_text and not clean_text.startswith("%") and "Downloading" not in clean_text:
            print(f"@LOG@{clean_text}")
            sys.stdout.flush()

    def flush(self):
        sys.stdout.flush()

def run_download_task(args):
    # args 应该是 [repo_id, cache_dir, target_root]
    if len(args) < 3:
        print("@ERROR@参数不足")
        return

    repo_id = args[0]
    cache_dir = args[1]
    target_root = args[2]

    try:
        from modelscope import snapshot_download
    except ImportError:
        print("@ERROR@未安装 modelscope")
        return

    sys.stderr = StreamAdapter()
    print(f"@LOG@正在启动下载进程...")
    print(f"@LOG@目标模型: {repo_id}")

    try:
        temp_path = snapshot_download(repo_id, cache_dir=cache_dir)
        temp_path_obj = Path(temp_path)
        print("@LOG@下载完成，正在整理文件...")
        model_name = temp_path_obj.name
        final_path = Path(target_root) / model_name
        if final_path.exists():
            print(f"@LOG@覆盖旧模型: {model_name}")
            shutil.rmtree(final_path)
        shutil.move(str(temp_path_obj), str(final_path))
        print(f"@FINISHED@{final_path}")
    except Exception as e:
        print(f"@ERROR@{str(e)}")

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        run_download_task(sys.argv[1:])