from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QListWidget, QGroupBox, QComboBox, QProgressBar, QLabel)
from PyQt6.QtCore import Qt
from app.config import PRESET_MODELS
from app.core.i18n import i18n

class ChatSidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(240)
        self.init_ui()
        
        # 初始刷新文本并连接信号
        self.update_texts()
        i18n.language_changed.connect(self.update_texts)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 新建对话
        self.btn_new_chat = QPushButton()
        self.btn_new_chat.setObjectName("PrimaryBtn")
        self.btn_new_chat.setStyleSheet("""
            QPushButton { background-color: #5aa9ff; color: #000; border-radius: 6px; font-weight: bold; padding: 6px; }
            QPushButton:hover { background-color: #4a99ef; }
        """)
        layout.addWidget(self.btn_new_chat)

        # 聊天列表
        self.chat_list = QListWidget()
        self.chat_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self.chat_list, 1)

        # 下载区域
        self.dl_group = QGroupBox()
        dl_layout = QVBoxLayout()
        
        self.combo_repo = QComboBox()
        self.combo_repo.setEditable(True)
        self.combo_repo.addItems(PRESET_MODELS)
        dl_layout.addWidget(self.combo_repo)

        # 按钮行
        dl_btns = QHBoxLayout()
        self.btn_download = QPushButton()
        self.btn_pause = QPushButton()
        self.btn_pause.setVisible(False)
        self.btn_stop = QPushButton()
        self.btn_stop.setObjectName("StopBtn")
        self.btn_stop.setVisible(False)
        
        dl_btns.addWidget(self.btn_download)
        dl_btns.addWidget(self.btn_pause)
        dl_btns.addWidget(self.btn_stop)
        dl_layout.addLayout(dl_btns)

        # 清空缓存
        self.btn_clear = QPushButton()
        self.btn_clear.setStyleSheet("""
            QPushButton { background-color: #2d3748; color: #aaa; border: 1px solid #3e4f65; border-radius: 4px; padding: 4px; font-size: 12px; }
            QPushButton:hover { background-color: #3e4f65; color: #fff; }
        """)
        dl_layout.addWidget(self.btn_clear)

        self.dl_progress = QProgressBar()
        self.dl_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dl_progress.setVisible(False)
        dl_layout.addWidget(self.dl_progress)
        
        self.lbl_dl_status = QLabel()
        self.lbl_dl_status.setStyleSheet("font-size: 11px; color: #888; margin-top:4px;")
        self.lbl_dl_status.setWordWrap(True)
        dl_layout.addWidget(self.lbl_dl_status)
        
        self.dl_group.setLayout(dl_layout)
        layout.addWidget(self.dl_group)

        # 运行设置
        self.run_group = QGroupBox()
        run_layout = QVBoxLayout()
        
        # === 语言选择 ===
        self.lbl_lang = QLabel()
        run_layout.addWidget(self.lbl_lang)
        self.combo_lang = QComboBox()
        # 手动添加支持的语言
        self.combo_lang.addItem("English", "en_US")
        self.combo_lang.addItem("简体中文", "zh_CN")
        self.combo_lang.currentIndexChanged.connect(self.on_lang_switch)
        run_layout.addWidget(self.combo_lang)
        # ================

        self.lbl_device = QLabel()
        run_layout.addWidget(self.lbl_device)
        self.combo_device = QComboBox()
        self.combo_device.addItems(["AUTO", "NPU", "GPU", "CPU"])
        run_layout.addWidget(self.combo_device)
        
        self.lbl_local_model = QLabel()
        run_layout.addWidget(self.lbl_local_model)
        self.combo_models = QComboBox()
        run_layout.addWidget(self.combo_models)
        
        self.btn_load = QPushButton()
        self.btn_load.setObjectName("PrimaryBtn")
        self.btn_load.setStyleSheet("""
            QPushButton { background-color: #5aa9ff; color: #000; border-radius: 6px; font-weight: bold; padding: 6px; }
            QPushButton:hover { background-color: #4a99ef; }
            QPushButton:disabled { background-color: #333; color: #777; }
        """)
        run_layout.addWidget(self.btn_load)

        # === 统计信息显示区域 ===
        self.lbl_stats_title = QLabel()
        self.lbl_stats_title.setStyleSheet("color: #6b7280; font-size: 11px; margin-top: 8px; font-weight: bold;")
        run_layout.addWidget(self.lbl_stats_title)

        self.lbl_stats_val = QLabel("--")
        self.lbl_stats_val.setStyleSheet("color: #22c55e; font-size: 12px; font-family: Consolas, monospace;")
        self.lbl_stats_val.setWordWrap(True)
        run_layout.addWidget(self.lbl_stats_val)
        # ===========================
        
        self.run_group.setLayout(run_layout)
        layout.addWidget(self.run_group)

    def on_lang_switch(self):
        code = self.combo_lang.currentData()
        if code != i18n.current_lang:
            i18n.load_language(code)

    def update_texts(self):
        """刷新界面文本"""
        self.btn_new_chat.setText(i18n.t("btn_new_chat"))
        
        self.dl_group.setTitle(i18n.t("group_download"))
        self.combo_repo.setPlaceholderText(i18n.t("placeholder_repo"))
        self.btn_download.setText(i18n.t("btn_download"))
        self.btn_pause.setText(i18n.t("btn_pause"))
        self.btn_stop.setText(i18n.t("btn_cancel"))
        self.btn_clear.setText(i18n.t("btn_clear_cache"))
        
        # 只在状态为空或"就绪"时重置，避免覆盖下载进度
        if not self.lbl_dl_status.text() or self.lbl_dl_status.text() in [i18n.t("status_ready"), "Ready", "就绪"]:
            self.lbl_dl_status.setText(i18n.t("status_ready"))

        self.run_group.setTitle(i18n.t("group_run"))
        self.lbl_lang.setText(i18n.t("label_language"))
        self.lbl_device.setText(i18n.t("label_device"))
        self.lbl_local_model.setText(i18n.t("label_model"))
        self.btn_load.setText(i18n.t("btn_load_model"))
        
        # 刷新统计
        self.lbl_stats_title.setText(i18n.t("label_stats"))

        # 同步下拉框显示
        idx = self.combo_lang.findData(i18n.current_lang)
        if idx >= 0:
            self.combo_lang.blockSignals(True)
            self.combo_lang.setCurrentIndex(idx)
            self.combo_lang.blockSignals(False)

    def set_stats(self, text):
        """设置统计信息文本"""
        self.lbl_stats_val.setText(text)