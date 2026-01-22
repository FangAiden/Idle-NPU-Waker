from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                             QPushButton, QLabel, QHBoxLayout, QMenu, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QAction
from app.ui.resources import MORE_ICON_SVG, TEMP_CHAT_ICON_SVG
from app.core.i18n import i18n
from app.utils.styles import (
    STYLE_LIST_WIDGET, STYLE_BTN_CHAT, STYLE_BTN_SESSION_MORE,
    STYLE_MENU_DARK, STYLE_LABEL_SESSION_TITLE, STYLE_BTN_TEMP_CHAT,
    STYLE_TEMP_SESSION_ITEM
)

class SessionItemWidget(QWidget):
    """会话项目控件"""
    sig_rename = pyqtSignal(str)
    sig_delete = pyqtSignal(str)

    def __init__(self, sid, title, is_temporary=False, parent=None):
        super().__init__(parent)
        self.sid = sid
        self.is_temporary = is_temporary
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 5, 5)
        layout.setSpacing(5)

        self.title_label = QLabel(title)
        if is_temporary:
            self.title_label.setStyleSheet(STYLE_TEMP_SESSION_ITEM)
        else:
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


class SessionListPanel(QWidget):
    """封装了新建按钮和会话列表"""
    sig_session_switch = pyqtSignal(str)
    sig_session_delete = pyqtSignal(str)
    sig_session_rename = pyqtSignal(str, str)
    sig_new_chat = pyqtSignal()
    sig_temp_chat = pyqtSignal()  # 新增：临时对话信号

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 按钮行：新建对话 + 临时对话
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_new_chat = QPushButton()
        self.btn_new_chat.clicked.connect(self.sig_new_chat.emit)
        self.btn_new_chat.setStyleSheet(STYLE_BTN_CHAT)
        self.btn_new_chat.setFixedHeight(44)
        btn_row.addWidget(self.btn_new_chat, 1)

        self.btn_temp_chat = QPushButton()
        self.btn_temp_chat.clicked.connect(self.sig_temp_chat.emit)
        self.btn_temp_chat.setStyleSheet(STYLE_BTN_TEMP_CHAT)
        self.btn_temp_chat.setFixedSize(44, 44)
        pix = QPixmap()
        pix.loadFromData(TEMP_CHAT_ICON_SVG)
        self.btn_temp_chat.setIcon(QIcon(pix))
        btn_row.addWidget(self.btn_temp_chat)

        layout.addLayout(btn_row)

        self.chat_list = QListWidget()
        self.chat_list.setStyleSheet(STYLE_LIST_WIDGET)
        self.chat_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.chat_list, 1)

        self.update_texts()
        i18n.language_changed.connect(self.update_texts)

    def add_session(self, sid, title, is_temporary=False):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, sid)
        item.setData(Qt.ItemDataRole.UserRole + 1, is_temporary)  # 存储临时标记
        item.setSizeHint(QSize(0, 40))

        widget = SessionItemWidget(sid, title, is_temporary=is_temporary)
        widget.sig_rename.connect(self._handle_rename_request)
        widget.sig_delete.connect(self.sig_session_delete.emit)

        self.chat_list.insertItem(0, item)
        self.chat_list.setItemWidget(item, widget)
        self.chat_list.setCurrentItem(item)

    def remove_session(self, sid):
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == sid:
                self.chat_list.takeItem(i)
                break

    def populate(self, sessions_dict, current_sid):
        self.chat_list.clear()
        if not sessions_dict: return
        for sid, data in sessions_dict.items():
            self.add_session(sid, data.get("title", "Untitled"))
        if current_sid:
            self.select_session(current_sid)

    def select_session(self, sid):
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == sid:
                self.chat_list.setCurrentItem(item)
                break

    def update_current_title(self, title):
        if self.chat_list.currentItem():
            item = self.chat_list.currentItem()
            widget = self.chat_list.itemWidget(item)
            if widget: widget.update_title(title)

    def _on_item_clicked(self, item):
        self.sig_session_switch.emit(item.data(Qt.ItemDataRole.UserRole))

    def _handle_rename_request(self, sid):
        text, ok = QInputDialog.getText(self, i18n.t("dialog_rename_title"), 
                                        i18n.t("dialog_rename_msg"), 
                                        text=i18n.t("default_chat_name"))
        if ok and text.strip():
            self.sig_session_rename.emit(sid, text.strip())
            for i in range(self.chat_list.count()):
                item = self.chat_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == sid:
                    widget = self.chat_list.itemWidget(item)
                    if widget: widget.update_title(text.strip())
                    break

    def update_texts(self):
        self.btn_new_chat.setText(i18n.t("btn_new_chat"))
        self.btn_temp_chat.setText(i18n.t("btn_temp_chat", "Temp"))
        self.btn_temp_chat.setToolTip(i18n.t("temp_chat_tooltip", "Temporary chats are not saved"))
