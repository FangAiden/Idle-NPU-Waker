from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QListWidget, QGroupBox, QComboBox, QProgressBar, QLabel)
from PyQt6.QtCore import Qt
from app.config import PRESET_MODELS

class ChatSidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(240)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 新建对话
        self.btn_new_chat = QPushButton("+ 新建对话")
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
        dl_group = QGroupBox("下载模型 (魔搭社区)")
        dl_layout = QVBoxLayout()
        
        self.combo_repo = QComboBox()
        self.combo_repo.setEditable(True)
        self.combo_repo.addItems(PRESET_MODELS)
        self.combo_repo.setPlaceholderText("选择或输入模型ID...")
        dl_layout.addWidget(self.combo_repo)

        # 按钮行: 下载/暂停/取消
        dl_btns = QHBoxLayout()
        self.btn_download = QPushButton("下载")
        self.btn_pause = QPushButton("暂停")
        self.btn_pause.setVisible(False)
        self.btn_stop = QPushButton("取消")
        self.btn_stop.setObjectName("StopBtn")
        self.btn_stop.setVisible(False)
        
        dl_btns.addWidget(self.btn_download)
        dl_btns.addWidget(self.btn_pause)
        dl_btns.addWidget(self.btn_stop)
        dl_layout.addLayout(dl_btns)

        # 按钮行: 清空缓存
        self.btn_clear = QPushButton("清空下载缓存")
        self.btn_clear.setStyleSheet("""
            QPushButton { background-color: #2d3748; color: #aaa; border: 1px solid #3e4f65; border-radius: 4px; padding: 4px; font-size: 12px; }
            QPushButton:hover { background-color: #3e4f65; color: #fff; }
        """)
        dl_layout.addWidget(self.btn_clear)

        self.dl_progress = QProgressBar()
        self.dl_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dl_progress.setVisible(False)
        dl_layout.addWidget(self.dl_progress)
        
        self.lbl_dl_status = QLabel("就绪")
        self.lbl_dl_status.setStyleSheet("font-size: 11px; color: #888; margin-top:4px;")
        self.lbl_dl_status.setWordWrap(True)
        dl_layout.addWidget(self.lbl_dl_status)
        
        dl_group.setLayout(dl_layout)
        layout.addWidget(dl_group)

        # 运行设置
        run_group = QGroupBox("运行设置")
        run_layout = QVBoxLayout()
        run_layout.addWidget(QLabel("设备:"))
        self.combo_device = QComboBox()
        self.combo_device.addItems(["AUTO", "NPU", "GPU", "CPU"])
        run_layout.addWidget(self.combo_device)
        
        run_layout.addWidget(QLabel("本地模型:"))
        self.combo_models = QComboBox()
        run_layout.addWidget(self.combo_models)
        
        self.btn_load = QPushButton("加载模型")
        self.btn_load.setObjectName("PrimaryBtn")
        self.btn_load.setStyleSheet("""
            QPushButton { background-color: #5aa9ff; color: #000; border-radius: 6px; font-weight: bold; padding: 6px; }
            QPushButton:hover { background-color: #4a99ef; }
            QPushButton:disabled { background-color: #333; color: #777; }
        """)
        run_layout.addWidget(self.btn_load)
        
        run_group.setLayout(run_layout)
        layout.addWidget(run_group)