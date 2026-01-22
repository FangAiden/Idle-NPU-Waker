from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QStackedWidget, QFrame, QLabel, QSizePolicy, QMenu)
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
    sig_temp_chat = pyqtSignal()  # 新增：临时对话信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(260)
        self.init_ui()
        i18n.language_changed.connect(self.update_texts)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.stack = QStackedWidget()
        
        self.page_chat = QWidget()
        chat_layout = QVBoxLayout(self.page_chat)
        chat_layout.setContentsMargins(12, 12, 12, 12)
        chat_layout.setSpacing(12)

        self.session_panel = SessionListPanel()
        self.session_panel.sig_new_chat.connect(self.sig_new_chat)
        self.session_panel.sig_temp_chat.connect(self.sig_temp_chat)  # 连接临时对话信号
        self.session_panel.sig_session_switch.connect(self.sig_session_switch)
        self.session_panel.sig_session_rename.connect(self.sig_session_rename)
        self.session_panel.sig_session_delete.connect(self.sig_session_delete)
        chat_layout.addWidget(self.session_panel, 1)

        self.stack.addWidget(self.page_chat)

        self.page_settings = QWidget()
        settings_layout = QVBoxLayout(self.page_settings)
        settings_layout.setContentsMargins(12, 12, 12, 12)
        settings_layout.setSpacing(12)

        self.run_panel = RuntimeControlPanel()
        self.run_panel.sig_load_model.connect(self.sig_model_load_requested)
        self.run_panel.sig_model_changed.connect(self.on_model_selection_changed)
        settings_layout.addWidget(self.run_panel)

        self.settings_panel = ModelSettingsPanel()
        settings_layout.addWidget(self.settings_panel, 1)

        self.stack.addWidget(self.page_settings)

        self.page_download = QWidget()
        download_layout = QVBoxLayout(self.page_download)
        download_layout.setContentsMargins(12, 12, 12, 12)
        download_layout.setSpacing(12)

        self.dl_panel = DownloadPanel()
        download_layout.addWidget(self.dl_panel)

        self.stack.addWidget(self.page_download)

        self.dl_panel.sig_download_finished.connect(lambda p: self.run_panel.scan_local_models())

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
        self.lbl_stats_val.setVisible(False)
        bottom_layout.addWidget(self.lbl_stats_val)

        self.btn_language = QPushButton()
        self.btn_language.setStyleSheet(STYLE_BTN_GHOST)
        self.btn_language.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_language.clicked.connect(self._show_language_menu)
        bottom_layout.addWidget(self.btn_language)

        self.btn_download = QPushButton()
        self.btn_download.setCheckable(True)
        self.btn_download.setStyleSheet(STYLE_BTN_GHOST)
        self.btn_download.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_download.clicked.connect(self.on_toggle_download)
        bottom_layout.addWidget(self.btn_download)

        self.btn_settings = QPushButton()
        self.btn_settings.setCheckable(True)
        self.btn_settings.setStyleSheet(STYLE_BTN_GHOST)
        self.btn_settings.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_settings.clicked.connect(self.on_toggle_settings)
        bottom_layout.addWidget(self.btn_settings)

        tools_layout = QHBoxLayout()
        tools_layout.setContentsMargins(0, 0, 0, 0)
        tools_layout.setSpacing(0)

        self.lbl_version = QLabel(f"v{APP_VERSION}")
        self.lbl_version.setStyleSheet(STYLE_LABEL_DIM)
        tools_layout.addWidget(self.lbl_version)
        tools_layout.addStretch()

        bottom_layout.addLayout(tools_layout)
        
        parent_layout.addWidget(bottom_bar)


    def populate_sessions(self, sessions, current_sid):
        self.session_panel.populate(sessions, current_sid)

    def add_session_item(self, sid, title, is_temporary=False):
        self.session_panel.add_session(sid, title, is_temporary=is_temporary)

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
        if hasattr(self, "lbl_stats_val"):
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

    def on_toggle_settings(self):
        current = self.stack.currentWidget()
        target = self.page_settings if current is not self.page_settings else self.page_chat
        self.stack.setCurrentWidget(target)
        self._sync_footer_buttons()

    def on_toggle_download(self):
        current = self.stack.currentWidget()
        target = self.page_download if current is not self.page_download else self.page_chat
        self.stack.setCurrentWidget(target)
        self._sync_footer_buttons()

    def _sync_footer_buttons(self):
        self.btn_settings.setChecked(self.stack.currentWidget() is self.page_settings)
        self.btn_download.setChecked(self.stack.currentWidget() is self.page_download)

    def update_texts(self):
        self.btn_settings.setText(i18n.t("btn_settings", "Settings"))
        self.btn_download.setText(i18n.t("btn_open_download", "Download"))
        self._update_language_label()
        self._sync_footer_buttons()

    def _update_language_label(self):
        label = "English" if i18n.current_lang.startswith("en") else "Chinese"
        self.btn_language.setText(label)
        self.btn_language.setToolTip(i18n.t("label_language", "Language"))

    def _show_language_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #171717; color: #ececec; border: 1px solid #444; }"
                           "QMenu::item { padding: 6px 20px; }"
                           "QMenu::item:selected { background-color: #2f2f2f; }")
        action_en = menu.addAction("English")
        action_zh = menu.addAction("Chinese")
        action = menu.exec(self.btn_language.mapToGlobal(self.btn_language.rect().bottomLeft()))
        if action == action_en:
            i18n.load_language("en_US")
        elif action == action_zh:
            i18n.load_language("zh_CN")
