from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QListWidget, QGroupBox, QComboBox, QProgressBar, QLabel,
                             QStackedWidget, QFrame, QMessageBox, QListWidgetItem, QSizePolicy,
                             QMenu, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QFileSystemWatcher, QSize
from PyQt6.QtGui import QIcon, QPixmap, QAction
from app.config import MODELS_DIR, DOWNLOAD_CACHE_DIR
from app.model_configs import PRESET_MODELS
from app.core.i18n import i18n
from app.ui.settings_panel import ModelSettingsPanel
from app.core.downloader import DownloadManager
from app.utils.scanner import scan_dirs
from app.utils.config_loader import load_model_json_configs
from app.ui.widgets import NoScrollComboBox
from app.ui.resources import MORE_ICON_SVG
from app.utils.styles import (
    STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY, STYLE_BTN_DANGER_DARK,
    STYLE_BTN_GHOST, STYLE_BTN_LINK, STYLE_LIST_WIDGET, STYLE_GROUP_BOX,
    STYLE_COMBOBOX, STYLE_LABEL_NORMAL, STYLE_PROGRESS_BAR,
    STYLE_BTN_SESSION_MORE, STYLE_MENU_DARK, STYLE_SIDEBAR_BOTTOM_BAR,
    STYLE_LABEL_SESSION_TITLE, STYLE_LABEL_STATS, STYLE_LABEL_STATUS_SMALL
)
import shutil
import os
import stat

class SessionItemWidget(QWidget):
    """自定义会话列表项，包含标题和更多按钮"""
    sig_rename = pyqtSignal(str)
    sig_delete = pyqtSignal(str)

    def __init__(self, sid, title, parent=None):
        super().__init__(parent)
        self.sid = sid
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 5, 5)
        layout.setSpacing(5)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(STYLE_LABEL_SESSION_TITLE)
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.title_label, 1)

        self.btn_more = QPushButton()
        self.btn_more.setFixedSize(24, 24)
        self.btn_more.setStyleSheet(STYLE_BTN_SESSION_MORE)
        pix = QPixmap()
        pix.loadFromData(MORE_ICON_SVG)
        self.btn_more.setIcon(QIcon(pix))
        self.btn_more.clicked.connect(self.show_menu)
        layout.addWidget(self.btn_more)

    def show_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(STYLE_MENU_DARK)
        
        act_rename = QAction(i18n.t("menu_rename_chat", "Rename"), self)
        act_rename.triggered.connect(lambda: self.sig_rename.emit(self.sid))
        menu.addAction(act_rename)
        
        act_delete = QAction(i18n.t("menu_delete_chat", "Delete"), self)
        act_delete.triggered.connect(lambda: self.sig_delete.emit(self.sid))
        menu.addAction(act_delete)
        
        menu.exec(self.btn_more.mapToGlobal(self.btn_more.rect().bottomLeft()))

    def update_title(self, new_title):
        self.title_label.setText(new_title)


class ChatSidebar(QWidget):
    sig_model_load_requested = pyqtSignal(str, str, str, str)
    sig_session_switch = pyqtSignal(str)
    sig_session_delete = pyqtSignal(str)
    sig_session_rename = pyqtSignal(str, str)
    sig_new_chat = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(280)
        self.dl_manager = DownloadManager()
        self.fs_watcher = QFileSystemWatcher()
        self._setup_internal_logic()
        self.init_ui()
        self.scan_local_models()
        self.update_texts()
        i18n.language_changed.connect(self.update_texts)

    def _setup_internal_logic(self):
        self.dl_manager.signal_progress.connect(self._on_dl_progress)
        self.dl_manager.signal_finished.connect(self._on_dl_finished)
        self.dl_manager.signal_log.connect(self._on_dl_log)
        self.dl_manager.signal_error.connect(self._on_dl_error)
        self.dl_manager.signal_process_state.connect(self._on_dl_state_change)
        
        if not MODELS_DIR.exists():
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
        self.fs_watcher.addPath(str(MODELS_DIR))
        self.fs_watcher.directoryChanged.connect(self.scan_local_models)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)

        self.page_chat = QWidget()
        layout_chat = QVBoxLayout(self.page_chat)
        layout_chat.setContentsMargins(10, 10, 10, 10)
        layout_chat.setSpacing(10)
        
        self.btn_new_chat = QPushButton()
        self.btn_new_chat.setObjectName("PrimaryBtn")
        self.btn_new_chat.clicked.connect(self.sig_new_chat.emit)
        self.btn_new_chat.setStyleSheet(STYLE_BTN_PRIMARY)
        layout_chat.addWidget(self.btn_new_chat)
        
        self.chat_list = QListWidget()
        self.chat_list.itemClicked.connect(self._on_item_clicked)
        self.chat_list.setStyleSheet(STYLE_LIST_WIDGET)
        layout_chat.addWidget(self.chat_list, 1)
        
        self.create_basic_controls(layout_chat)
        self.stack.addWidget(self.page_chat)

        self.settings_panel = ModelSettingsPanel()
        self.stack.addWidget(self.settings_panel)

        bottom_bar = QFrame()
        bottom_bar.setStyleSheet(STYLE_SIDEBAR_BOTTOM_BAR)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(10, 8, 10, 8)
        bottom_layout.setSpacing(10)
        
        self.btn_toggle_view = QPushButton()
        self.btn_toggle_view.setCheckable(True)
        self.btn_toggle_view.clicked.connect(self.on_toggle_view)
        self.btn_toggle_view.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.btn_toggle_view.setStyleSheet(STYLE_BTN_GHOST)
        
        self.lbl_stats_val = QLabel("--")
        self.lbl_stats_val.setStyleSheet(STYLE_LABEL_STATS)
        self.lbl_stats_val.setWordWrap(False)
        self.lbl_stats_val.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lbl_stats_val.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        bottom_layout.addWidget(self.lbl_stats_val, 55)
        bottom_layout.addWidget(self.btn_toggle_view, 45)
        
        main_layout.addWidget(bottom_bar)

    def create_basic_controls(self, layout):
        self.dl_group = QGroupBox()
        self.dl_group.setStyleSheet(STYLE_GROUP_BOX)
        dl_layout = QVBoxLayout()
        dl_layout.setSpacing(8)
        
        self.combo_repo = NoScrollComboBox()
        self.combo_repo.setEditable(True)
        self.combo_repo.addItems(PRESET_MODELS)
        self.combo_repo.setStyleSheet(STYLE_COMBOBOX)
        dl_layout.addWidget(self.combo_repo)

        dl_btns = QHBoxLayout()
        self.btn_download = QPushButton()
        self.btn_download.clicked.connect(self.start_download)
        self.btn_download.setStyleSheet(STYLE_BTN_SECONDARY)
        
        self.btn_pause = QPushButton()
        self.btn_pause.clicked.connect(self.dl_manager.pause_download)
        self.btn_pause.setVisible(False)
        self.btn_pause.setStyleSheet(STYLE_BTN_SECONDARY)
        
        self.btn_stop = QPushButton()
        self.btn_stop.setObjectName("StopBtn")
        self.btn_stop.clicked.connect(self.dl_manager.stop_download)
        self.btn_stop.setVisible(False)
        self.btn_stop.setStyleSheet(STYLE_BTN_DANGER_DARK)

        dl_btns.addWidget(self.btn_download)
        dl_btns.addWidget(self.btn_pause)
        dl_btns.addWidget(self.btn_stop)
        dl_layout.addLayout(dl_btns)

        self.btn_clear = QPushButton()
        self.btn_clear.clicked.connect(self.clear_cache)
        self.btn_clear.setStyleSheet(STYLE_BTN_LINK)
        dl_layout.addWidget(self.btn_clear, alignment=Qt.AlignmentFlag.AlignRight)

        self.dl_progress = QProgressBar()
        self.dl_progress.setVisible(False)
        self.dl_progress.setFixedHeight(12)
        self.dl_progress.setStyleSheet(STYLE_PROGRESS_BAR)
        dl_layout.addWidget(self.dl_progress)
        
        self.lbl_dl_status = QLabel()
        self.lbl_dl_status.setStyleSheet(STYLE_LABEL_STATUS_SMALL)
        self.lbl_dl_status.setWordWrap(True)
        dl_layout.addWidget(self.lbl_dl_status)
        
        self.dl_group.setLayout(dl_layout)
        layout.addWidget(self.dl_group)

        self.run_group = QGroupBox()
        self.run_group.setStyleSheet(STYLE_GROUP_BOX)
        run_layout = QVBoxLayout()
        run_layout.setSpacing(10)
        
        self.lbl_lang = QLabel()
        self.lbl_lang.setStyleSheet(STYLE_LABEL_NORMAL)
        run_layout.addWidget(self.lbl_lang)
        
        self.combo_lang = NoScrollComboBox()
        self.combo_lang.addItem("English", "en_US")
        self.combo_lang.addItem("简体中文", "zh_CN")
        self.combo_lang.setStyleSheet(STYLE_COMBOBOX)
        self.combo_lang.currentIndexChanged.connect(self.on_lang_switch)
        run_layout.addWidget(self.combo_lang)

        self.lbl_device = QLabel()
        self.lbl_device.setStyleSheet(STYLE_LABEL_NORMAL)
        run_layout.addWidget(self.lbl_device)
        
        self.combo_device = NoScrollComboBox()
        self.combo_device.addItems(["AUTO", "NPU", "GPU", "CPU"])
        self.combo_device.setStyleSheet(STYLE_COMBOBOX)
        run_layout.addWidget(self.combo_device)
        
        self.lbl_local_model = QLabel()
        self.lbl_local_model.setStyleSheet(STYLE_LABEL_NORMAL)
        run_layout.addWidget(self.lbl_local_model)
        
        self.combo_models = NoScrollComboBox()
        self.combo_models.setStyleSheet(STYLE_COMBOBOX)
        self.combo_models.currentIndexChanged.connect(self.on_model_changed)
        run_layout.addWidget(self.combo_models)
        
        self.btn_load = QPushButton()
        self.btn_load.setObjectName("PrimaryBtn")
        self.btn_load.clicked.connect(self.request_load_model)
        self.btn_load.setStyleSheet(STYLE_BTN_PRIMARY + "QPushButton { margin-top: 5px; }")
        run_layout.addWidget(self.btn_load)
        
        self.run_group.setLayout(run_layout)
        layout.addWidget(self.run_group)

    def scan_local_models(self):
        curr = self.combo_models.currentText()
        models = scan_dirs([MODELS_DIR])
        self.combo_models.blockSignals(True)
        self.combo_models.clear()
        for m in models: self.combo_models.addItem(f"{m['name']}", m['path'])
        
        idx = self.combo_models.findText(curr)
        if idx >= 0: self.combo_models.setCurrentIndex(idx)
        elif self.combo_models.count() > 0: self.combo_models.setCurrentIndex(0)
        self.combo_models.blockSignals(False)
        self.on_model_changed()

    def start_download(self):
        rid = self.combo_repo.currentText().strip()
        if rid: self.dl_manager.start_download(rid)

    def _on_dl_state_change(self, running):
        self.btn_download.setVisible(not running)
        self.btn_pause.setVisible(running)
        self.btn_stop.setVisible(running)
        self.btn_clear.setEnabled(not running)
        self.combo_repo.setEnabled(not running)
        self.dl_progress.setVisible(running or self.dl_progress.value()>0)
        if running:
            self.dl_progress.setFormat("...")
            self.dl_progress.setRange(0, 0)

    def _on_dl_progress(self, f, p):
        self.dl_progress.setRange(0, 100)
        self.dl_progress.setValue(p)
        self.dl_progress.setFormat(f"{p}%")
        self.lbl_dl_status.setText(i18n.t("status_downloading").format(f))

    def _on_dl_finished(self, p):
        self.lbl_dl_status.setText(i18n.t("status_ready"))
        self.scan_local_models()
        self.combo_models.setCurrentIndex(self.combo_models.findText(Path(p).name))
        self.dl_progress.setValue(100)
        QMessageBox.information(self, i18n.t("dialog_success"), i18n.t("dialog_model_ready").format(Path(p).name))

    def _on_dl_log(self, m): self.lbl_dl_status.setText(m)
    def _on_dl_error(self, e): 
        self.lbl_dl_status.setText(f"❌ {e}")
        self.dl_progress.setVisible(False)

    def clear_cache(self):
        self.dl_manager.stop_download()
        reply = QMessageBox.question(self, i18n.t("dialog_confirm_clear"), i18n.t("dialog_clear_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.lbl_dl_status.setText(i18n.t("status_cleaning"))
            QApplication.processEvents()
            def on_rm_error(func, path, exc_info):
                os.chmod(path, stat.S_IWRITE)
                try: func(path)
                except: pass 
            if DOWNLOAD_CACHE_DIR.exists():
                shutil.rmtree(DOWNLOAD_CACHE_DIR, onerror=on_rm_error)
            DOWNLOAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            QMessageBox.information(self, i18n.t("dialog_success"), i18n.t("dialog_cache_cleared"))
            self.lbl_dl_status.setText(i18n.t("status_ready"))
            self.dl_progress.setValue(0)

    def request_load_model(self):
        p = self.combo_models.currentData()
        d = self.combo_device.currentText()
        if p:
            self.lbl_dl_status.setText(i18n.t("status_loading_model").format(Path(p).name))
            self.btn_load.setEnabled(False)
            self.sig_model_load_requested.emit("local", "", p, d)

    def on_model_load_result(self, success, msg):
        self.btn_load.setEnabled(True)
        if success:
            self.lbl_dl_status.setText(i18n.t("status_loaded").format(msg))
        else:
            self.lbl_dl_status.setText("Error")

    def add_session_item(self, sid, title):
        """添加会话项，使用自定义 Widget"""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, sid)
        item.setSizeHint(QSize(0, 40))
        
        widget = SessionItemWidget(sid, title)
        widget.sig_rename.connect(self._handle_rename_request)
        widget.sig_delete.connect(self.sig_session_delete.emit)
        
        self.chat_list.insertItem(0, item)
        self.chat_list.setItemWidget(item, widget)
        self.chat_list.setCurrentItem(item)

    def update_current_session_title(self, title):
        if self.chat_list.currentItem():
            item = self.chat_list.currentItem()
            widget = self.chat_list.itemWidget(item)
            if widget:
                widget.update_title(title)

    def _on_item_clicked(self, item):
        self.sig_session_switch.emit(item.data(Qt.ItemDataRole.UserRole))

    def _handle_rename_request(self, sid):
        text, ok = QInputDialog.getText(self, i18n.t("dialog_rename_title", "Rename Chat"), 
                                        i18n.t("dialog_rename_msg", "Enter new name:"), 
                                        text=i18n.t("default_chat_name"))
        if ok and text.strip():
            self.sig_session_rename.emit(sid, text.strip())
            for i in range(self.chat_list.count()):
                item = self.chat_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == sid:
                    widget = self.chat_list.itemWidget(item)
                    if widget:
                        widget.update_title(text.strip())
                    break

    def populate_sessions(self, sessions_dict, current_sid):
        """启动时加载所有会话"""
        self.chat_list.clear()
        if not sessions_dict: return

        for sid, data in sessions_dict.items():
            self.add_session_item(sid, data.get("title", "Untitled"))
        
        if current_sid:
            for i in range(self.chat_list.count()):
                item = self.chat_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == current_sid:
                    self.chat_list.setCurrentItem(item)
                    break

    def remove_session_item(self, sid):
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == sid:
                self.chat_list.takeItem(i)
                break

    def shutdown(self):
        self.dl_manager.stop_download()

    def on_model_changed(self):
        model_name = self.combo_models.currentText()
        model_path = self.combo_models.currentData()

        if hasattr(self, 'settings_panel'):
            self.settings_panel.apply_preset(model_name)
            
            if model_path:
                try:
                    dynamic_conf = load_model_json_configs(model_path)
                    if dynamic_conf:
                        print(f"Loaded dynamic config for {model_name}: {dynamic_conf}")
                        self.settings_panel.apply_dynamic_config(dynamic_conf)
                except Exception as e:
                    print(f"Failed to load dynamic config: {e}")

    def get_current_config(self):
        if hasattr(self, 'settings_panel'):
            return self.settings_panel.get_config()
        return {}

    def on_toggle_view(self, checked):
        self.stack.setCurrentIndex(1 if checked else 0)
        self.update_texts()

    def on_lang_switch(self):
        code = self.combo_lang.currentData()
        if code != i18n.current_lang:
            i18n.load_language(code)

    def set_stats(self, text):
        self.lbl_stats_val.setText(text)

    def update_texts(self):
        self.btn_new_chat.setText(i18n.t("btn_new_chat"))
        self.dl_group.setTitle(i18n.t("group_download"))
        self.combo_repo.setPlaceholderText(i18n.t("placeholder_repo"))
        self.btn_download.setText(i18n.t("btn_download"))
        self.btn_pause.setText(i18n.t("btn_pause"))
        self.btn_stop.setText(i18n.t("btn_cancel"))
        self.btn_clear.setText(i18n.t("btn_clear_cache"))
        if not self.lbl_dl_status.text() or self.lbl_dl_status.text() in [i18n.t("status_ready"), "Ready", "就绪"]:
            self.lbl_dl_status.setText(i18n.t("status_ready"))
        self.run_group.setTitle(i18n.t("group_run"))
        self.lbl_lang.setText(i18n.t("label_language"))
        self.lbl_device.setText(i18n.t("label_device"))
        self.lbl_local_model.setText(i18n.t("label_model"))
        self.btn_load.setText(i18n.t("btn_load_model"))
        if self.btn_toggle_view.isChecked():
            self.btn_toggle_view.setText("← " + i18n.t("btn_back_chat", "Back"))
        else:
            self.btn_toggle_view.setText("⚙️ " + i18n.t("btn_settings", "Settings"))
        idx = self.combo_lang.findData(i18n.current_lang)
        if idx >= 0:
            self.combo_lang.blockSignals(True)
            self.combo_lang.setCurrentIndex(idx)
            self.combo_lang.blockSignals(False)