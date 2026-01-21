from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QStackedWidget, QFrame, QLabel, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal

from app.core.i18n import i18n
from app.ui.settings_panel import ModelSettingsPanel
from app.ui.components.session_list import SessionListPanel
from app.ui.components.download_panel import DownloadPanel
from app.ui.components.runtime_panel import RuntimeControlPanel
from app.config import APP_VERSION 
from app.utils.styles import (
    STYLE_BTN_GHOST, STYLE_SIDEBAR_BOTTOM_BAR, 
    STYLE_LABEL_STATS, STYLE_LABEL_DIM
)
from app.utils.config_loader import load_model_json_configs

class ChatSidebar(QWidget):
    sig_model_load_requested = pyqtSignal(str, str, str, str)
    sig_session_switch = pyqtSignal(str)
    sig_session_delete = pyqtSignal(str)
    sig_session_rename = pyqtSignal(str, str)
    sig_new_chat = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(280)
        self.init_ui()
        i18n.language_changed.connect(self.update_texts)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.stack = QStackedWidget()
        
        self.page_chat = QWidget()
        chat_layout = QVBoxLayout(self.page_chat)
        chat_layout.setContentsMargins(10, 10, 10, 10)
        chat_layout.setSpacing(10)

        self.session_panel = SessionListPanel()
        self.session_panel.sig_new_chat.connect(self.sig_new_chat)
        self.session_panel.sig_session_switch.connect(self.sig_session_switch)
        self.session_panel.sig_session_rename.connect(self.sig_session_rename)
        self.session_panel.sig_session_delete.connect(self.sig_session_delete)
        chat_layout.addWidget(self.session_panel, 1)

        self.dl_panel = DownloadPanel()
        chat_layout.addWidget(self.dl_panel)

        self.run_panel = RuntimeControlPanel()
        self.run_panel.sig_load_model.connect(self.sig_model_load_requested)
        self.run_panel.sig_model_changed.connect(self.on_model_selection_changed)
        chat_layout.addWidget(self.run_panel)
        
        self.dl_panel.sig_download_finished.connect(lambda p: self.run_panel.scan_local_models())

        self.stack.addWidget(self.page_chat)

        self.settings_panel = ModelSettingsPanel()
        self.stack.addWidget(self.settings_panel)

        main_layout.addWidget(self.stack, 1)

        self.build_bottom_bar(main_layout)
        
        self.update_texts()

    def build_bottom_bar(self, parent_layout):
        bottom_bar = QFrame()
        bottom_bar.setStyleSheet(STYLE_SIDEBAR_BOTTOM_BAR)
        
        bottom_layout = QVBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(10, 8, 10, 8)
        bottom_layout.setSpacing(4)
        
        self.lbl_stats_val = QLabel("--")
        self.lbl_stats_val.setStyleSheet(STYLE_LABEL_STATS)
        self.lbl_stats_val.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lbl_stats_val.setAlignment(Qt.AlignmentFlag.AlignLeft)
        bottom_layout.addWidget(self.lbl_stats_val)

        tools_layout = QHBoxLayout()
        tools_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_version = QLabel(f"v{APP_VERSION}")
        self.lbl_version.setStyleSheet(STYLE_LABEL_DIM)
        tools_layout.addWidget(self.lbl_version)
        
        tools_layout.addStretch()
        
        self.btn_toggle_view = QPushButton()
        self.btn_toggle_view.setCheckable(True)
        self.btn_toggle_view.clicked.connect(self.on_toggle_view)
        self.btn_toggle_view.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_toggle_view.setStyleSheet(STYLE_BTN_GHOST)
        tools_layout.addWidget(self.btn_toggle_view)

        bottom_layout.addLayout(tools_layout)
        
        parent_layout.addWidget(bottom_bar)


    def populate_sessions(self, sessions, current_sid):
        self.session_panel.populate(sessions, current_sid)

    def add_session_item(self, sid, title):
        self.session_panel.add_session(sid, title)

    def remove_session_item(self, sid):
        self.session_panel.remove_session(sid)

    def update_current_session_title(self, title):
        self.session_panel.update_current_title(title)

    def on_model_load_result(self, success, dev):
        self.run_panel.on_load_finished(success)
        if success:
            self.dl_panel.lbl_status.setText(i18n.t("status_loaded").format(dev))
        else:
            self.dl_panel.lbl_status.setText("Load Failed")

    def set_stats(self, text):
        self.lbl_stats_val.setText(text)

    def get_current_config(self):
        return self.settings_panel.get_config()

    def shutdown(self):
        self.dl_panel.stop()

    def on_model_selection_changed(self, name, path):
        """当 RunPanel 选择了新模型，更新 SettingsPanel"""
        self.settings_panel.apply_supported_settings(name, path)
        self.settings_panel.apply_preset(name)
        if path:
            try:
                dynamic_conf = load_model_json_configs(path)
                if dynamic_conf:
                    self.settings_panel.apply_dynamic_config(dynamic_conf)
            except: pass

    def on_toggle_view(self, checked):
        self.stack.setCurrentIndex(1 if checked else 0)
        self.update_texts()

    def update_texts(self):
        if self.btn_toggle_view.isChecked():
            self.btn_toggle_view.setText("← " + i18n.t("btn_back_chat", "Back"))
        else:
            self.btn_toggle_view.setText("⚙️ " + i18n.t("btn_settings", "Settings"))
