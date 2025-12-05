import sys
import os
import traceback
import multiprocessing
import ctypes
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon, QPixmap

from app.core.i18n import i18n

multiprocessing.freeze_support()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    with open("crash.log", "w", encoding="utf-8") as f:
        f.write(error_msg)
    
    print("CRITICAL ERROR:", error_msg)
    
    try:
        if QApplication.instance():
            title = i18n.t("crash_title", "Application Crash")
            msg = i18n.t("crash_message", "An unhandled exception occurred.\n\n{0}").format(exc_value)
            QMessageBox.critical(None, title, msg)
    except:
        pass

sys.excepthook = global_exception_handler

def main():
    try:
        myappid = 'idle.npu.waker.1.0' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    # 处理独立下载进程的参数
    if len(sys.argv) > 1 and sys.argv[1] == "--worker-download":
        from app.core.download_script import run_download_task
        run_download_task(sys.argv[2:])
        return

    from app.ui.chat_window import ChatWindow
    from app.ui.resources import APP_ICON_SVG 

    app = QApplication(sys.argv)
    
    i18n.auto_init()
    
    app_icon = QPixmap()
    app_icon.loadFromData(APP_ICON_SVG)
    app.setWindowIcon(QIcon(app_icon))

    win = ChatWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()