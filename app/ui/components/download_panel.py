import os
import stat
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QGroupBox, QProgressBar, QLabel, QMessageBox, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal
from app.config import DOWNLOAD_CACHE_DIR
from app.model_configs import PRESET_MODELS
from app.core.downloader import DownloadManager
from app.core.i18n import i18n
from app.ui.widgets import NoScrollComboBox
from app.utils.styles import (
    STYLE_GROUP_BOX, STYLE_COMBOBOX, STYLE_BTN_SECONDARY, 
    STYLE_BTN_DANGER_DARK, STYLE_BTN_LINK, STYLE_PROGRESS_BAR, STYLE_LABEL_STATUS_SMALL
)

class DownloadPanel(QGroupBox):
    sig_download_finished = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dl_manager = DownloadManager()
        self._init_ui()
        self._connect_signals()
        self.update_texts()
        i18n.language_changed.connect(self.update_texts)

    def _init_ui(self):
        self.setStyleSheet(STYLE_GROUP_BOX)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self.combo_repo = NoScrollComboBox()
        self.combo_repo.setEditable(True)
        self.combo_repo.addItems(PRESET_MODELS)
        self.combo_repo.setStyleSheet(STYLE_COMBOBOX)
        layout.addWidget(self.combo_repo)

        btns_layout = QHBoxLayout()
        self.btn_download = QPushButton()
        self.btn_download.clicked.connect(self.start_download)
        self.btn_download.setStyleSheet(STYLE_BTN_SECONDARY)
        
        self.btn_pause = QPushButton()
        self.btn_pause.clicked.connect(self.dl_manager.pause_download)
        self.btn_pause.setVisible(False)
        self.btn_pause.setStyleSheet(STYLE_BTN_SECONDARY)
        
        self.btn_stop = QPushButton()
        self.btn_stop.clicked.connect(self.dl_manager.stop_download)
        self.btn_stop.setVisible(False)
        self.btn_stop.setStyleSheet(STYLE_BTN_DANGER_DARK)

        btns_layout.addWidget(self.btn_download)
        btns_layout.addWidget(self.btn_pause)
        btns_layout.addWidget(self.btn_stop)
        layout.addLayout(btns_layout)

        self.btn_clear = QPushButton()
        self.btn_clear.clicked.connect(self.clear_cache)
        self.btn_clear.setStyleSheet(STYLE_BTN_LINK)
        layout.addWidget(self.btn_clear, alignment=Qt.AlignmentFlag.AlignRight)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setStyleSheet(STYLE_PROGRESS_BAR)
        layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel()
        self.lbl_status.setStyleSheet(STYLE_LABEL_STATUS_SMALL)
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

    def _connect_signals(self):
        self.dl_manager.signal_progress.connect(self._on_progress)
        self.dl_manager.signal_finished.connect(self._on_finished)
        self.dl_manager.signal_log.connect(lambda m: self.lbl_status.setText(m))
        self.dl_manager.signal_error.connect(self._on_error)
        self.dl_manager.signal_process_state.connect(self._on_state_change)

    def start_download(self):
        rid = self.combo_repo.currentText().strip()
        if rid: self.dl_manager.start_download(rid)

    def clear_cache(self):
        self.dl_manager.stop_download()
        reply = QMessageBox.question(self, i18n.t("dialog_confirm_clear"), i18n.t("dialog_clear_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.lbl_status.setText(i18n.t("status_cleaning"))
            QApplication.processEvents()
            def on_rm_error(func, path, exc_info):
                os.chmod(path, stat.S_IWRITE)
                try: func(path)
                except: pass 
            if DOWNLOAD_CACHE_DIR.exists():
                shutil.rmtree(DOWNLOAD_CACHE_DIR, onerror=on_rm_error)
            DOWNLOAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            QMessageBox.information(self, i18n.t("dialog_success"), i18n.t("dialog_cache_cleared"))
            self.lbl_status.setText(i18n.t("status_ready"))
            self.progress_bar.setValue(0)

    def _on_state_change(self, running):
        self.btn_download.setVisible(not running)
        self.btn_pause.setVisible(running)
        self.btn_stop.setVisible(running)
        self.btn_clear.setEnabled(not running)
        self.combo_repo.setEnabled(not running)
        self.progress_bar.setVisible(running or self.progress_bar.value() > 0)
        if running:
            self.progress_bar.setFormat("...")
            self.progress_bar.setRange(0, 0)

    def _on_progress(self, f, p):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(p)
        self.progress_bar.setFormat(f"{p}%")
        self.lbl_status.setText(i18n.t("status_downloading").format(f))

    def _on_finished(self, path):
        self.lbl_status.setText(i18n.t("status_ready"))
        self.progress_bar.setValue(100)
        QMessageBox.information(self, i18n.t("dialog_success"), i18n.t("dialog_model_ready").format(Path(path).name))
        self.sig_download_finished.emit(path)

    def _on_error(self, e):
        self.lbl_status.setText(f"❌ {e}")
        self.progress_bar.setVisible(False)

    def update_texts(self):
        self.setTitle(i18n.t("group_download"))
        self.combo_repo.setPlaceholderText(i18n.t("placeholder_repo"))
        self.btn_download.setText(i18n.t("btn_download"))
        self.btn_pause.setText(i18n.t("btn_pause"))
        self.btn_stop.setText(i18n.t("btn_cancel"))
        self.btn_clear.setText(i18n.t("btn_clear_cache"))
        if not self.lbl_status.text() or self.lbl_status.text() in ["Ready", "就绪"]:
            self.lbl_status.setText(i18n.t("status_ready"))

    def stop(self):
        self.dl_manager.stop_download()