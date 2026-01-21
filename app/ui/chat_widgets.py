from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QLineEdit, QPushButton, QStackedWidget, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QPixmap
from app.ui.message_bubble import MessageBubble
from app.ui.resources import CHEVRON_ICON_SVG
from app.core.i18n import i18n
from app.utils.styles import (
    STYLE_BTN_PRIMARY, STYLE_BTN_DANGER, STYLE_INPUT_BOX,
    STYLE_SCROLL_AREA, STYLE_CHAT_INPUT_BAR, STYLE_BTN_SCROLL_BOTTOM,
    STYLE_BTN_SECONDARY, STYLE_LABEL_DIM
)

class ChatHistoryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.layout_main = QVBoxLayout(self)
        self.layout_main.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(STYLE_SCROLL_AREA)
        
        self.v_scrollbar = self.scroll_area.verticalScrollBar()
        self.v_scrollbar.valueChanged.connect(self._on_scroll_changed)
        self._stick_to_bottom = True
        
        self.msg_container = QWidget()
        self.msg_container.setStyleSheet("background-color: transparent;")
        
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setContentsMargins(20, 20, 20, 20)
        self.msg_layout.setSpacing(15)
        self.msg_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.msg_container)
        self.layout_main.addWidget(self.scroll_area)

        self.btn_scroll_bottom = QPushButton(self)
        self.btn_scroll_bottom.setFixedSize(40, 40)
        self.btn_scroll_bottom.setStyleSheet(STYLE_BTN_SCROLL_BOTTOM)
        self.btn_scroll_bottom.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scroll_bottom.clicked.connect(lambda: self.scroll_to_bottom(force=True))
        self.btn_scroll_bottom.hide()
        
        pix = QPixmap()
        pix.loadFromData(CHEVRON_ICON_SVG)
        self.btn_scroll_bottom.setIcon(QIcon(pix))
        self.btn_scroll_bottom.setIconSize(QSize(20, 20))

    def showEvent(self, event):
        """窗口显示事件：确保在界面完全显示后强制刷新一次气泡宽度"""
        super().showEvent(event)
        QTimer.singleShot(0, self._adjust_bubbles_width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        padding = 20
        scroll_width = self.v_scrollbar.width() if self.v_scrollbar.isVisible() else 0
        x = self.width() - self.btn_scroll_bottom.width() - padding - scroll_width
        y = self.height() - self.btn_scroll_bottom.height() - padding
        self.btn_scroll_bottom.move(x, y)
        self.btn_scroll_bottom.raise_()

        self._adjust_bubbles_width()

    def _adjust_bubbles_width(self):
        """让所有气泡响应当前窗口宽度"""
        viewport_width = self.scroll_area.viewport().width()
        if viewport_width <= 0: return

        available_width = viewport_width - 40
        
        for i in range(self.msg_layout.count()):
            item = self.msg_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, MessageBubble):
                widget.adjust_width(available_width)

    def _on_scroll_changed(self, value):
        if not self.v_scrollbar: return
        
        max_val = self.v_scrollbar.maximum()
        dist_to_bottom = max_val - value
        is_at_bottom = dist_to_bottom <= 50
        
        self._stick_to_bottom = is_at_bottom
        
        if not is_at_bottom and max_val > 0:
            self.btn_scroll_bottom.show()
        else:
            self.btn_scroll_bottom.hide()

    def add_bubble(self, text, is_user=False, think_duration=None, message_index=None):
        bubble = MessageBubble(text, is_user=is_user, think_duration=think_duration, message_index=message_index)
        
        viewport_width = self.scroll_area.viewport().width()
        if viewport_width > 40:
            bubble.adjust_width(viewport_width - 40)
            
        self.msg_layout.addWidget(bubble)
        self.scroll_to_bottom(force=False)
        return bubble

    def clear(self):
        while self.msg_layout.count():
            item = self.msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def scroll_to_bottom(self, smart=False, force=False):
        """
        滚动到底部
        :param smart: 如果为 True，则只有在用户原本就在底部时才滚动（防打扰模式）
        :param force: 强制滚动到底部（用于按钮点击）
        """
        if smart and not self._stick_to_bottom and not force:
            return

        QTimer.singleShot(10, lambda: self.v_scrollbar.setValue(
            self.v_scrollbar.maximum()
        ))


class ChatInputBar(QWidget):
    sig_send = pyqtSignal(str)
    sig_stop = pyqtSignal()
    sig_attach = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._attachment_names = []
        self.init_ui()
        i18n.language_changed.connect(self.update_texts)

    def init_ui(self):
        self.setStyleSheet(STYLE_CHAT_INPUT_BAR)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(6)

        self.lbl_attachments = QLabel()
        self.lbl_attachments.setStyleSheet(STYLE_LABEL_DIM)
        self.lbl_attachments.setVisible(False)
        layout.addWidget(self.lbl_attachments)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        self.input_box = QLineEdit()
        self.input_box.returnPressed.connect(self.on_send_clicked)
        self.input_box.setStyleSheet(STYLE_INPUT_BOX)
        row.addWidget(self.input_box)

        self.btn_attach = QPushButton()
        self.btn_attach.setStyleSheet(STYLE_BTN_SECONDARY)
        self.btn_attach.setFixedHeight(36)
        self.btn_attach.setFixedWidth(80)
        self.btn_attach.clicked.connect(self.sig_attach.emit)
        row.addWidget(self.btn_attach)

        self.btn_stack = QStackedWidget()
        self.btn_stack.setFixedSize(80, 40)
        self.btn_stack.setStyleSheet("border: none;")

        self.btn_send = QPushButton() 
        self.btn_send.setStyleSheet(STYLE_BTN_PRIMARY)
        self.btn_send.clicked.connect(self.on_send_clicked)
        self.btn_stack.addWidget(self.btn_send)
        
        self.btn_stop = QPushButton() 
        self.btn_stop.setStyleSheet(STYLE_BTN_DANGER)
        self.btn_stop.clicked.connect(self.on_stop_clicked)
        self.btn_stack.addWidget(self.btn_stop)

        row.addWidget(self.btn_stack)
        layout.addLayout(row)
        self.update_texts()

    def on_send_clicked(self):
        txt = self.input_box.text().strip()
        if txt:
            self.sig_send.emit(txt)

    def on_stop_clicked(self):
        self.sig_stop.emit()

    def set_generating(self, is_generating):
        self.btn_stack.setCurrentIndex(1 if is_generating else 0)
        self.input_box.setEnabled(not is_generating)
        self.btn_attach.setEnabled(not is_generating)
        if not is_generating:
            self.input_box.setFocus()

    def clear_input(self):
        self.input_box.clear()

    def set_attachments(self, names):
        self._attachment_names = [name for name in names if name]
        if self._attachment_names:
            label = i18n.t("label_attachments", "Attachments")
            self.lbl_attachments.setText(f"{label}: {', '.join(self._attachment_names)}")
            self.lbl_attachments.setVisible(True)
        else:
            self.lbl_attachments.setVisible(False)

    def update_texts(self):
        self.input_box.setPlaceholderText(i18n.t("input_placeholder"))
        self.btn_send.setText(i18n.t("btn_send"))
        self.btn_stop.setText(i18n.t("btn_stop"))
        self.btn_attach.setText(i18n.t("btn_attach", "Attach"))
        if self._attachment_names:
            label = i18n.t("label_attachments", "Attachments")
            self.lbl_attachments.setText(f"{label}: {', '.join(self._attachment_names)}")
