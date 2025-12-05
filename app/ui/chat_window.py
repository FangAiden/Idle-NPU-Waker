import uuid
import shutil
import os
import stat
import time
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                             QLineEdit, QPushButton, QComboBox, 
                             QLabel, QMessageBox, QListWidget, QListWidgetItem,
                             QGroupBox, QProgressBar, QSplitter, QScrollArea, QApplication, QStackedWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QFileSystemWatcher, QTimer, QSize
from PyQt6.QtGui import QIcon, QPixmap

from app.core.llm_worker import AIWorker
from app.core.downloader import DownloadManager
from app.core.runtime import RuntimeState
from app.utils.scanner import scan_dirs
from app.utils.styles import MAIN_STYLESHEET
from app.config import MODELS_DIR, PRESET_MODELS, DOWNLOAD_CACHE_DIR 

from app.ui.message_bubble import MessageBubble
from app.ui.resources import APP_ICON_SVG

class ChatWindow(QMainWindow):
    sig_do_load = pyqtSignal(str, str, str, str)
    sig_do_generate = pyqtSignal(str, dict)
    sig_start_download = pyqtSignal(str)
    sig_pause_download = pyqtSignal()
    sig_stop_download = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Idle NPU Waker")
        self.resize(1200, 850)
        icon_pix = QPixmap()
        icon_pix.loadFromData(APP_ICON_SVG)
        self.setWindowIcon(QIcon(icon_pix))
        self.setStyleSheet(MAIN_STYLESHEET)

        self.runtime = RuntimeState()
        self.thread_ai = QThread()
        self.worker_ai = AIWorker(self.runtime)
        self.worker_ai.moveToThread(self.thread_ai)
        
        self.dl_manager = DownloadManager()

        self.fs_watcher = QFileSystemWatcher()
        if not MODELS_DIR.exists():
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
        self.fs_watcher.addPath(str(MODELS_DIR))
        self.fs_watcher.directoryChanged.connect(self.on_models_dir_changed)

        self._connect_signals()
        self.thread_ai.start()

        self.sessions = {}
        self.current_session_id = None
        self.current_ai_bubble = None 
        
        self.setup_ui()
        self.scan_local_models()
        self.create_new_chat()

    def _connect_signals(self):
        self.sig_do_load.connect(self.worker_ai.load_model)
        self.sig_do_generate.connect(self.worker_ai.generate)
        self.worker_ai.signal_model_loaded.connect(self.on_model_loaded)
        self.worker_ai.signal_token.connect(self.on_token_received)
        self.worker_ai.signal_finished.connect(self.on_generation_finished)
        self.worker_ai.signal_error.connect(self.on_error)

        self.sig_start_download.connect(self.dl_manager.start_download)
        self.sig_pause_download.connect(self.dl_manager.pause_download)
        self.sig_stop_download.connect(self.dl_manager.stop_download)
        self.dl_manager.signal_log.connect(self.on_download_log)
        self.dl_manager.signal_progress.connect(self.on_download_progress)
        self.dl_manager.signal_finished.connect(self.on_download_finished)
        self.dl_manager.signal_error.connect(self.on_download_error)
        self.dl_manager.signal_process_state.connect(self.on_download_state_changed)

    def setup_ui(self):
        from app.ui.sidebar import ChatSidebar
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background-color: #1e2842; }")

        # --- Sidebar ---
        self.sidebar = ChatSidebar()
        self.sidebar.btn_new_chat.clicked.connect(self.create_new_chat)
        self.sidebar.chat_list.itemClicked.connect(self.on_chat_selected)
        self.sidebar.chat_list.customContextMenuRequested.connect(self.show_chat_context_menu)
        
        self.sidebar.btn_download.clicked.connect(self.do_download_action)
        self.sidebar.btn_pause.clicked.connect(self.do_pause_action)
        self.sidebar.btn_stop.clicked.connect(self.do_stop_action)
        self.sidebar.btn_clear.clicked.connect(self.do_clear_cache)
        self.sidebar.btn_load.clicked.connect(self.do_load_model)
        
        splitter.addWidget(self.sidebar)

        # --- Main Area ---
        main_area = QWidget()
        main_inner = QVBoxLayout(main_area)
        main_inner.setContentsMargins(0, 0, 0, 0)
        main_inner.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #0b0f19; }")
        
        self.msg_container = QWidget()
        self.msg_container.setStyleSheet("background-color: #0b0f19;")
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setContentsMargins(20, 20, 20, 20)
        self.msg_layout.setSpacing(15)
        self.msg_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.msg_container)
        main_inner.addWidget(self.scroll_area, 1)

        input_container = QWidget()
        input_container.setStyleSheet("background-color: #0b0f19; border-top: 1px solid #1e2842;")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(20, 15, 20, 15)
        
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("输入消息 (Enter 发送)...")
        self.input_box.returnPressed.connect(self.do_send)
        self.input_box.setStyleSheet("QLineEdit { background-color: #0e1525; border: 1px solid #1e2842; border-radius: 8px; padding: 10px; color: #e6e8ee; font-size: 14px; } QLineEdit:focus { border: 1px solid #5aa9ff; }")

        self.btn_stack = QStackedWidget()
        self.btn_stack.setFixedSize(80, 40)
        
        self.btn_send = QPushButton("发送")
        self.btn_send.setStyleSheet("QPushButton { background-color: #5aa9ff; color: #000; border-radius: 6px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #4a99ef; }")
        self.btn_send.clicked.connect(self.do_send)
        self.btn_stack.addWidget(self.btn_send)
        
        self.btn_stop_gen = QPushButton("停止")
        self.btn_stop_gen.setStyleSheet("QPushButton { background-color: #f08a5d; color: #000; border-radius: 6px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #e07a4d; }")
        self.btn_stop_gen.clicked.connect(self.do_stop_gen)
        self.btn_stack.addWidget(self.btn_stop_gen)

        input_layout.addWidget(self.input_box)
        input_layout.addWidget(self.btn_stack)
        main_inner.addWidget(input_container)
        
        splitter.addWidget(main_area)
        splitter.setSizes([280, 920])
        splitter.setCollapsible(0, False)
        main_layout.addWidget(splitter)

    # ================= 业务逻辑 =================

    def do_clear_cache(self):
        self.dl_manager.stop_download()
        QApplication.processEvents() 
        
        size_info = ""
        try:
            total_size = sum(f.stat().st_size for f in DOWNLOAD_CACHE_DIR.glob('**/*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            size_info = f"\n占用: {size_mb:.2f} MB"
        except: pass

        reply = QMessageBox.question(self, "确认清空", 
                                     f"确定要强力清除缓存吗？{size_info}\n如果文件被占用，程序将尝试强制解锁。",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return

        def on_rm_error(func, path, exc_info):
            os.chmod(path, stat.S_IWRITE)
            try: func(path)
            except Exception: pass 

        self.sidebar.lbl_dl_status.setText("正在清理缓存...")
        QApplication.processEvents()
        
        success = False
        for i in range(3): 
            try:
                if DOWNLOAD_CACHE_DIR.exists():
                    shutil.rmtree(DOWNLOAD_CACHE_DIR, onerror=on_rm_error)
                success = True
                break
            except Exception as e:
                time.sleep(0.5)
        
        if success:
            try:
                DOWNLOAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                QMessageBox.information(self, "成功", "缓存已成功清空！")
                self.sidebar.lbl_dl_status.setText("缓存已清理")
                self.sidebar.dl_progress.setValue(0)
                self.sidebar.dl_progress.setFormat("")
            except: pass
        else:
            QMessageBox.warning(self, "警告", "部分文件仍被占用，请重启软件后再次尝试清理。")

    def create_new_chat(self):
        sid = str(uuid.uuid4())
        self.sessions[sid] = {"title": "新对话", "history": []}
        item = QListWidgetItem("新对话")
        item.setData(Qt.ItemDataRole.UserRole, sid)
        self.sidebar.chat_list.insertItem(0, item)
        self.sidebar.chat_list.setCurrentItem(item)
        self.switch_session(sid)

    def show_chat_context_menu(self, pos):
        item = self.sidebar.chat_list.itemAt(pos)
        if not item: return
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #1e2842; color: #fff; border: 1px solid #333; } QMenu::item { padding: 5px 20px; } QMenu::item:selected { background-color: #5aa9ff; color: #000; }")
        del_action = QAction("删除会话", self)
        del_action.triggered.connect(lambda: self.delete_session(item))
        menu.addAction(del_action)
        menu.exec(self.sidebar.chat_list.mapToGlobal(pos))

    def delete_session(self, item):
        sid = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, '确认删除', f'确定要删除会话 "{item.text()}" 吗?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if sid in self.sessions: del self.sessions[sid]
            row = self.sidebar.chat_list.row(item)
            self.sidebar.chat_list.takeItem(row)
            if sid == self.current_session_id:
                if self.sidebar.chat_list.count() > 0:
                    new_item = self.sidebar.chat_list.item(0)
                    self.sidebar.chat_list.setCurrentItem(new_item)
                    self.on_chat_selected(new_item)
                else:
                    self.create_new_chat()

    def on_chat_selected(self, item):
        sid = item.data(Qt.ItemDataRole.UserRole)
        if sid != self.current_session_id: self.switch_session(sid)

    def switch_session(self, sid):
        self.current_session_id = sid
        self.clear_messages()
        history = self.sessions[sid]["history"]
        for msg in history:
            self.add_bubble(msg["content"], is_user=(msg["role"]=="user"))

    def _update_title(self, txt):
        if not self.current_session_id: return
        t = txt[:10] + ("..." if len(txt)>10 else "")
        self.sessions[self.current_session_id]["title"] = t
        if self.sidebar.chat_list.currentItem():
            self.sidebar.chat_list.currentItem().setText(t)

    def clear_messages(self):
        while self.msg_layout.count():
            item = self.msg_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.current_ai_bubble = None

    def add_bubble(self, text, is_user=False):
        bubble = MessageBubble(text, is_user=is_user)
        self.msg_layout.addWidget(bubble)
        QApplication.processEvents()
        self.scroll_to_bottom()
        return bubble

    def scroll_to_bottom(self):
        QTimer.singleShot(10, lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum()))

    def scan_local_models(self):
        curr = self.sidebar.combo_models.currentText()
        models = scan_dirs([MODELS_DIR])
        self.sidebar.combo_models.blockSignals(True)
        self.sidebar.combo_models.clear()
        for m in models: self.sidebar.combo_models.addItem(f"{m['name']}", m['path'])
        idx = self.sidebar.combo_models.findText(curr)
        if idx >= 0: self.sidebar.combo_models.setCurrentIndex(idx)
        elif self.sidebar.combo_models.count() > 0: self.sidebar.combo_models.setCurrentIndex(0)
        self.sidebar.combo_models.blockSignals(False)

    def on_models_dir_changed(self, p): self.scan_local_models()
    def do_download_action(self):
        rid = self.sidebar.combo_repo.currentText().strip()
        if rid: self.sig_start_download.emit(rid)
    def do_pause_action(self): self.sig_pause_download.emit()
    def do_stop_action(self): self.sig_stop_download.emit()
    def on_download_state_changed(self, running):
        self.sidebar.btn_download.setVisible(not running)
        self.sidebar.btn_pause.setVisible(running)
        self.sidebar.btn_stop.setVisible(running)
        self.sidebar.btn_clear.setEnabled(not running)
        self.sidebar.combo_repo.setEnabled(not running)
        self.sidebar.dl_progress.setVisible(running or self.sidebar.dl_progress.value()>0)
        if running:
            self.sidebar.dl_progress.setFormat("连接中...")
            self.sidebar.dl_progress.setRange(0, 0)
    def on_download_progress(self, f, p):
        self.sidebar.dl_progress.setRange(0, 100)
        self.sidebar.dl_progress.setValue(p)
        self.sidebar.dl_progress.setFormat(f"{p}%")
        self.sidebar.lbl_dl_status.setText(f"下载中: {f}")
    def on_download_finished(self, p):
        self.sidebar.lbl_dl_status.setText("✅ 完成")
        self.scan_local_models()
        self.sidebar.combo_models.setCurrentIndex(self.sidebar.combo_models.findText(Path(p).name))
        self.sidebar.dl_progress.setValue(100)
        self.sidebar.dl_progress.setFormat("100%")
        QMessageBox.information(self, "成功", f"模型已就绪:\n{Path(p).name}")
    def on_download_log(self, m): self.sidebar.lbl_dl_status.setText(m)
    def on_download_error(self, e): 
        self.sidebar.lbl_dl_status.setText(f"❌ {e}")
        self.sidebar.dl_progress.setVisible(False)
    def do_send(self):
        txt = self.input_box.text().strip()
        if not txt: return
        if not self.runtime.tokenizer:
            QMessageBox.warning(self, "提示", "请先加载模型")
            return
        self.add_bubble(txt, is_user=True)
        self.input_box.clear()
        sess = self.sessions[self.current_session_id]
        if not sess["history"]: self._update_title(txt)
        sess["history"].append({"role":"user", "content":txt})
        self.btn_stack.setCurrentIndex(1)
        self.current_ai_buffer = ""
        self.current_ai_bubble = self.add_bubble("思考中...", is_user=False)
        try:
            prompt = self.runtime.tokenizer.apply_chat_template(sess["history"], add_generation_prompt=True, tokenize=False)
        except: prompt = txt
        self.sig_do_generate.emit(prompt, {"max_new_tokens": 1024})
    def on_token_received(self, text):
        self.current_ai_buffer += text
        if self.current_ai_bubble:
            self.current_ai_bubble.update_text(self.current_ai_buffer)
            self.scroll_to_bottom()
    def on_generation_finished(self):
        self.sessions[self.current_session_id]["history"].append({"role": "assistant", "content": self.current_ai_buffer})
        self.current_ai_bubble = None
        self.btn_stack.setCurrentIndex(0)
    def do_stop_gen(self): self.worker_ai.stop()
    def do_load_model(self):
        p = self.sidebar.combo_models.currentData()
        d = self.sidebar.combo_device.currentText()
        if p:
            self.sidebar.lbl_dl_status.setText(f"加载中: {Path(p).name}")
            self.sidebar.btn_load.setEnabled(False)
            self.btn_stack.setEnabled(False)
            self.sig_do_load.emit("local", "", p, d)
    def on_model_loaded(self, mid, dev):
        self.sidebar.lbl_dl_status.setText(f"✅ 已加载 ({dev})")
        self.sidebar.btn_load.setEnabled(True)
        self.btn_stack.setEnabled(True)
        QMessageBox.information(self, "就绪", f"模型加载成功 ({dev})")
    def on_error(self, e):
        self.sidebar.btn_load.setEnabled(True)
        self.btn_stack.setEnabled(True)
        self.btn_stack.setCurrentIndex(0)
        QMessageBox.critical(self, "错误", e)
        if self.current_ai_bubble:
            self.current_ai_bubble.update_text(self.current_ai_buffer + f"\n[错误: {e}]")
    def closeEvent(self, e):
        self.dl_manager.stop_download()
        self.worker_ai.stop()
        self.thread_ai.quit()
        self.thread_ai.wait(1000)
        super().closeEvent(e)