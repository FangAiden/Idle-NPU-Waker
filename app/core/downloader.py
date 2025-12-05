import sys
import os
import re
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QProcess
from app.config import DOWNLOAD_CACHE_DIR, MODELS_DIR
from app.core.i18n import i18n

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "download_script.py")
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class DownloadManager(QObject):
    signal_log = pyqtSignal(str)
    signal_progress = pyqtSignal(str, int)
    signal_finished = pyqtSignal(str)
    signal_error = pyqtSignal(str)
    signal_process_state = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.process = None
        self._manual_stop = False

    @pyqtSlot(str)
    def start_download(self, repo_id):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.signal_log.emit(i18n.t("dl_task_running"))
            return

        self._manual_stop = False
        
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        if getattr(sys, 'frozen', False):
            program = sys.executable
            args = ["--worker-download", repo_id, str(DOWNLOAD_CACHE_DIR), str(MODELS_DIR)]
        else:
            program = sys.executable
            script_abs_path = os.path.abspath(SCRIPT_PATH)
            args = [script_abs_path, repo_id, str(DOWNLOAD_CACHE_DIR), str(MODELS_DIR)]

        self.process.setProgram(program)
        self.process.setArguments(args)
        
        self.process.readyReadStandardOutput.connect(self._handle_output)
        self.process.finished.connect(self._on_process_finished)
        
        self.process.start()
        
        self.signal_log.emit(i18n.t("dl_init_process"))
        self.signal_process_state.emit(True)

    @pyqtSlot()
    def pause_download(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self._manual_stop = True
            self.process.kill()
            self.signal_log.emit(i18n.t("dl_paused"))

    @pyqtSlot()
    def stop_download(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self._manual_stop = True
            self.process.kill()
            self.signal_log.emit(i18n.t("dl_cancelled"))

    def _handle_output(self):
        data = self.process.readAllStandardOutput().data()
        try:
            text = data.decode('utf-8', errors='ignore')
        except:
            return

        for line in text.splitlines():
            line = ANSI_ESCAPE.sub('', line).strip()
            if not line: continue

            if line.startswith("@PROGRESS@"):
                parts = line.split("@")
                if len(parts) >= 4:
                    self.signal_progress.emit(parts[2], int(parts[3]))
            
            elif line.startswith("@FINISHED@"):
                parts = line.split("@")
                if len(parts) >= 3:
                    self.signal_finished.emit(parts[2])
            
            elif line.startswith("@ERROR@"):
                parts = line.split("@")
                if len(parts) >= 3:
                    self.signal_error.emit(parts[2])
            
            elif line.startswith("@LOG@"):
                content = line[5:]
                if content: self.signal_log.emit(content)
            
            else:
                if "Traceback" in line or "Error" in line or "Exception" in line:
                    self.signal_log.emit(i18n.t("dl_sys_prefix").format(line))

    def _on_process_finished(self, exit_code, exit_status):
        self.signal_process_state.emit(False)
        
        if self._manual_stop:
            return

        if exit_code != 0 or exit_status == QProcess.ExitStatus.CrashExit:
            error_msg = i18n.t("dl_error_exit").format(exit_code)
            if exit_code == 1:
                error_msg += i18n.t("dl_error_reason")
            
            self.signal_error.emit(error_msg)