from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal, QFileSystemWatcher
from app.config import MODELS_DIR
from app.core.i18n import i18n
from app.utils.scanner import scan_dirs
from app.ui.widgets import NoScrollComboBox
from app.utils.styles import (
    STYLE_GROUP_BOX, STYLE_LABEL_NORMAL, STYLE_COMBOBOX, STYLE_BTN_PRIMARY
)

class RuntimeControlPanel(QGroupBox):
    sig_load_model = pyqtSignal(str, str, str, str)
    sig_model_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fs_watcher = QFileSystemWatcher()
        self._init_ui()
        self._setup_watcher()
        self.update_texts()
        i18n.language_changed.connect(self.update_texts)
        self.scan_local_models()

    def _init_ui(self):
        self.setStyleSheet(STYLE_GROUP_BOX)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.lbl_device = QLabel()
        self.lbl_device.setStyleSheet(STYLE_LABEL_NORMAL)
        layout.addWidget(self.lbl_device)
        self.combo_device = NoScrollComboBox()
        self.combo_device.addItems(["AUTO", "NPU", "GPU", "CPU"])
        self.combo_device.setStyleSheet(STYLE_COMBOBOX)
        layout.addWidget(self.combo_device)

        self.lbl_model = QLabel()
        self.lbl_model.setStyleSheet(STYLE_LABEL_NORMAL)
        layout.addWidget(self.lbl_model)
        self.combo_models = NoScrollComboBox()
        self.combo_models.setStyleSheet(STYLE_COMBOBOX)
        self.combo_models.currentIndexChanged.connect(self._on_combo_model_changed)
        layout.addWidget(self.combo_models)

        self.btn_load = QPushButton()
        self.btn_load.clicked.connect(self._on_load_clicked)
        self.btn_load.setStyleSheet(STYLE_BTN_PRIMARY + "QPushButton { margin-top: 5px; }")
        layout.addWidget(self.btn_load)

    def _setup_watcher(self):
        if not MODELS_DIR.exists():
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
        self.fs_watcher.addPath(str(MODELS_DIR))
        self.fs_watcher.directoryChanged.connect(self.scan_local_models)

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
        self._on_combo_model_changed()

    def _on_combo_model_changed(self):
        name = self.combo_models.currentText()
        path = self.combo_models.currentData()
        self.sig_model_changed.emit(name, path)

    def _on_load_clicked(self):
        path = self.combo_models.currentData()
        dev = self.combo_device.currentText()
        if path:
            self.btn_load.setEnabled(False)
            self.sig_load_model.emit("local", "", path, dev)

    def on_load_finished(self, success):
        self.btn_load.setEnabled(True)

    def update_texts(self):
        self.setTitle(i18n.t("group_run"))
        self.lbl_device.setText(i18n.t("label_device"))
        self.lbl_model.setText(i18n.t("label_model"))
        self.btn_load.setText(i18n.t("btn_load_model"))
