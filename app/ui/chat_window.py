import time
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QMessageBox, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap

from app.core.llm_worker import AIWorker
from app.core.session import SessionManager
from app.ui.sidebar import ChatSidebar
from app.ui.chat_widgets import ChatHistoryPanel, ChatInputBar
from app.ui.resources import APP_ICON_SVG
from app.core.i18n import i18n
from app.utils.styles import MAIN_STYLESHEET, STYLE_SPLITTER

class ChatWindow(QMainWindow):
    sig_worker_load = pyqtSignal(str, str, str, str)
    sig_worker_gen = pyqtSignal(list, dict)

    def __init__(self):
        super().__init__()
        self.resize(1200, 850)
        self.setStyleSheet(MAIN_STYLESHEET)
        
        pix = QPixmap()
        pix.loadFromData(APP_ICON_SVG)
        self.setWindowIcon(QIcon(pix))

        self.session_mgr = SessionManager()
        
        self.thread_ai = QThread()
        self.worker_ai = AIWorker()
        self.worker_ai.moveToThread(self.thread_ai)
        
        self._connect_worker_signals()
        self.thread_ai.start()

        self.setup_ui()
        
        self.gen_start_time = 0
        self.stream_token_count = 0
        self.current_ai_buffer = ""
        self.current_ai_bubble = None
        
        self.is_model_loaded = False 
        self.current_model_path = None 
        
        if self.session_mgr.sessions:
            self.sidebar.populate_sessions(self.session_mgr.sessions, self.session_mgr.current_session_id)
            if self.session_mgr.current_session_id:
                self.do_switch_session(self.session_mgr.current_session_id)
            else:
                first_sid = list(self.session_mgr.sessions.keys())[0]
                self.do_switch_session(first_sid)
        else:
            self.do_new_chat()

    def _connect_worker_signals(self):
        self.sig_worker_load.connect(self.worker_ai.load_model)
        self.sig_worker_gen.connect(self.worker_ai.generate)
        
        self.worker_ai.signal_model_loaded.connect(self.on_model_loaded)
        self.worker_ai.signal_token.connect(self.on_token_received)
        self.worker_ai.signal_finished.connect(self.on_generation_finished)
        self.worker_ai.signal_error.connect(self.on_error)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(STYLE_SPLITTER)

        self.sidebar = ChatSidebar()
        self.history_panel = ChatHistoryPanel()
        self.input_bar = ChatInputBar()

        self.sidebar.sig_new_chat.connect(self.do_new_chat)
        self.sidebar.sig_session_switch.connect(self.do_switch_session)
        self.sidebar.sig_model_load_requested.connect(self.do_load_model)
        self.sidebar.sig_session_delete.connect(self.do_delete_session)
        self.sidebar.sig_session_rename.connect(self.do_rename_session)

        self.input_bar.sig_send.connect(self.do_send)
        self.input_bar.sig_stop.connect(self.worker_ai.stop)

        right_area = QWidget()
        right_layout = QVBoxLayout(right_area)
        right_layout.setContentsMargins(0,0,0,0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.history_panel, 1)
        right_layout.addWidget(self.input_bar)

        splitter.addWidget(self.sidebar)
        splitter.addWidget(right_area)
        splitter.setSizes([280, 920])
        splitter.setCollapsible(0, False)
        
        main_layout.addWidget(splitter)
        
        self.setWindowTitle(i18n.t("app_title"))
        i18n.language_changed.connect(lambda: self.setWindowTitle(i18n.t("app_title")))

    def do_load_model(self, src, mid, path, dev):
        if self.is_model_loaded and self.current_model_path == path:
            if hasattr(self.sidebar, 'on_model_load_result'):
                self.sidebar.on_model_load_result(True, dev)
            msg = i18n.t("status_loaded").format(i18n.t("msg_already_loaded"))
            QMessageBox.information(self, i18n.t("dialog_loaded_title"), msg)
            return

        self.pending_model_path = path 
        self.sig_worker_load.emit(src, mid, path, dev)

    def on_model_loaded(self, mid, dev):
        self.is_model_loaded = True
        if hasattr(self, 'pending_model_path'):
            self.current_model_path = self.pending_model_path
            
        if hasattr(self.sidebar, 'on_model_load_result'):
            self.sidebar.on_model_load_result(True, dev)
        QMessageBox.information(self, i18n.t("dialog_loaded_title"), i18n.t("dialog_loaded_msg").format(dev))

    def do_send(self, text):
        if not self.is_model_loaded:
            QMessageBox.warning(self, i18n.t("app_title"), i18n.t("tip_load_model_first"))
            return

        self.history_panel.add_bubble(text, is_user=True)
        self.input_bar.clear_input()
        self.input_bar.set_generating(True)

        sess_id = self.session_mgr.current_session_id
        if not self.session_mgr.get_current_history():
            new_title = self.session_mgr.update_title(text)
            self.sidebar.update_current_session_title(new_title)
            
        self.session_mgr.add_message("user", text)

        self.current_ai_buffer = ""
        self.current_ai_bubble = self.history_panel.add_bubble(i18n.t("msg_thinking"), is_user=False)

        gen_config = self.sidebar.get_current_config()

        sys_prompt = gen_config.get("system_prompt", "")
        max_turns = gen_config.get("max_history_turns", 10)
        
        full_history = self.session_mgr.get_current_history()

        if max_turns > 0:
            sliced_history = full_history[-(max_turns * 2):]
        else:
            sliced_history = [full_history[-1]] if full_history else []

        messages = []
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})
        messages.extend(sliced_history)

        self.gen_start_time = time.time()
        self.stream_token_count = 0
        self.sidebar.set_stats("...")

        self.sig_worker_gen.emit(messages, gen_config)

    def on_token_received(self, token):
        self.current_ai_buffer += token
        self.stream_token_count += 1

        if self.current_ai_bubble:
            self.current_ai_bubble.update_text(self.current_ai_buffer)
            self.history_panel.scroll_to_bottom(smart=True)

        now = time.time()
        if now - self.gen_start_time > 0.1:
            tps = self.stream_token_count / (now - self.gen_start_time)
            pattern = i18n.t("stats_pattern", "{0} tokens · {1:.1f} t/s · {2:.1f} s")
            self.sidebar.set_stats(pattern.format(self.stream_token_count, tps, now - self.gen_start_time))

    def on_generation_finished(self):
        self.input_bar.set_generating(False)
        
        think_duration = None
        if self.current_ai_bubble and self.current_ai_bubble.think_duration is not None:
            think_duration = self.current_ai_bubble.think_duration
            
        self.current_ai_bubble = None
        self.session_mgr.add_message("assistant", self.current_ai_buffer, think_duration=think_duration)

        try:
            duration = time.time() - self.gen_start_time
            count = self.stream_token_count
            tps = count / duration if duration > 0.01 else 0
            pattern = i18n.t("stats_pattern", "{0} tokens · {1:.1f} t/s · {2:.1f} s")
            self.sidebar.set_stats(pattern.format(count, tps, duration))
        except: pass

    def on_error(self, err_msg):
        self.input_bar.set_generating(False)
        if hasattr(self.sidebar, 'on_model_load_result'):
            self.sidebar.on_model_load_result(False, "")
        
        self.current_model_path = None
        
        QMessageBox.critical(self, i18n.t("dialog_error"), err_msg)
        if self.current_ai_bubble:
            self.current_ai_bubble.update_text(self.current_ai_buffer + f"\n[Error: {err_msg}]")

    def do_new_chat(self):
        sid = self.session_mgr.create_session(i18n.t("default_chat_name"))
        self.sidebar.add_session_item(sid, i18n.t("default_chat_name"))
        self.history_panel.clear()

    def do_switch_session(self, sid):
        self.session_mgr.current_session_id = sid
        self.history_panel.clear()
        history = self.session_mgr.get_current_history()
        for msg in history:
            think_duration = msg.get("think_duration")
            self.history_panel.add_bubble(msg["content"], is_user=(msg["role"]=="user"), think_duration=think_duration)

    def do_rename_session(self, sid, new_title):
        self.session_mgr.rename_session(sid, new_title)

    def do_delete_session(self, sid):
        session = self.session_mgr.get_session(sid)
        if not session: return
        
        reply = QMessageBox.question(self, i18n.t("dialog_confirm_delete"), 
                                     i18n.t("dialog_delete_msg").format(session.get("title", "")),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            is_current = (self.session_mgr.current_session_id == sid)
            
            self.session_mgr.delete_session(sid)
            self.sidebar.remove_session_item(sid)
            
            if is_current:
                if self.session_mgr.sessions:
                    first_sid = list(self.session_mgr.sessions.keys())[0]
                    self.sidebar.session_panel.chat_list.setCurrentRow(0)
                    self.do_switch_session(first_sid)
                else:
                    self.do_new_chat()

    def closeEvent(self, event):
        self.sidebar.shutdown()
        if hasattr(self.worker_ai, 'cleanup'):
            self.worker_ai.cleanup()
        else:
            self.worker_ai.stop()
            
        self.thread_ai.quit()
        self.thread_ai.wait(1000)
        super().closeEvent(event)