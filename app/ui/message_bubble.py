import re
import html
import time
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                             QPushButton, QApplication, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QTransform, QDesktopServices
from PyQt6.QtCore import QUrl
from app.ui.resources import AI_AVATAR_SVG, USER_AVATAR_SVG, COPY_ICON_SVG, CHEVRON_ICON_SVG
from app.core.i18n import i18n
from app.utils.styles import (
    STYLE_BTN_THINK_TOGGLE, STYLE_THINK_FRAME, STYLE_THINK_LABEL,
    STYLE_CONTENT_BUBBLE_BASE, STYLE_BTN_ICON_ONLY, MARKDOWN_CSS,
    COLOR_BUBBLE_USER, COLOR_BUBBLE_AI
)

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

class MessageBubble(QWidget):
    def __init__(self, text, is_user=False, think_duration=None, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.full_text = text
        self.thinking_expanded = True
        
        self.think_start_time = None
        self.think_duration = think_duration
        self.is_currently_thinking = False
        
        self.init_ui()
        
        i18n.language_changed.connect(self.refresh_ui_text)

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(12)

        self.avatar_lbl = QLabel()
        self.avatar_lbl.setFixedSize(36, 36)
        pixmap = QPixmap()
        if pixmap.loadFromData(USER_AVATAR_SVG if self.is_user else AI_AVATAR_SVG):
            self.avatar_lbl.setPixmap(pixmap)
        else:
            color = '#5aa9ff' if self.is_user else '#10a37f'
            self.avatar_lbl.setStyleSheet(f"background-color: {color}; border-radius: 18px;")
        self.avatar_lbl.setScaledContents(True)
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(4)

        self.btn_think_toggle = QPushButton("")
        self.btn_think_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_think_toggle.setVisible(False)
        self.btn_think_toggle.setStyleSheet(STYLE_BTN_THINK_TOGGLE)
        self.btn_think_toggle.setIconSize(QSize(16, 16))
        self.btn_think_toggle.clicked.connect(self.toggle_think)
        self.content_layout.addWidget(self.btn_think_toggle)

        self.think_frame = QFrame()
        self.think_frame.setVisible(False)
        self.think_frame.setStyleSheet(STYLE_THINK_FRAME)
        think_layout = QVBoxLayout(self.think_frame)
        think_layout.setContentsMargins(10, 8, 10, 8)

        self.think_lbl = QLabel()
        self.think_lbl.setWordWrap(True)
        self.think_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.think_lbl.setStyleSheet(STYLE_THINK_LABEL)
        think_layout.addWidget(self.think_lbl)
        self.content_layout.addWidget(self.think_frame)

        self.content_lbl = QLabel()
        self.content_lbl.setWordWrap(True)
        self.content_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.content_lbl.setOpenExternalLinks(True)
        self.content_lbl.linkActivated.connect(self.open_link)
        
        bg_color = COLOR_BUBBLE_USER if self.is_user else COLOR_BUBBLE_AI
        self.content_lbl.setStyleSheet(STYLE_CONTENT_BUBBLE_BASE + f"QLabel {{ background-color: {bg_color}; }}")
        self.content_layout.addWidget(self.content_lbl)

        self.btn_copy = QPushButton()
        self.btn_copy.setFixedSize(24, 24)
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setStyleSheet(STYLE_BTN_ICON_ONLY)
        cp_pix = QPixmap()
        cp_pix.loadFromData(COPY_ICON_SVG)
        self.btn_copy.setIcon(QIcon(cp_pix))
        self.btn_copy.clicked.connect(self.copy_text)

        if self.is_user:
            layout.addStretch()
            layout.addWidget(self.btn_copy, alignment=Qt.AlignmentFlag.AlignBottom)
            layout.addWidget(self.content_container)
            layout.addWidget(self.avatar_lbl, alignment=Qt.AlignmentFlag.AlignTop)
            self.content_container.setMaximumWidth(650)
        else:
            layout.addWidget(self.avatar_lbl, alignment=Qt.AlignmentFlag.AlignTop)
            layout.addWidget(self.content_container)
            layout.addWidget(self.btn_copy, alignment=Qt.AlignmentFlag.AlignBottom)
            layout.addStretch()
            self.content_container.setFixedWidth(750) 

        self.update_display_text(self.full_text)
        self.update_toggle_icon()

    def open_link(self, url):
        QDesktopServices.openUrl(QUrl(url))

    def update_toggle_icon(self):
        pix = QPixmap()
        pix.loadFromData(CHEVRON_ICON_SVG)
        if not self.thinking_expanded:
            transform = QTransform().rotate(-90)
            pix = pix.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        self.btn_think_toggle.setIcon(QIcon(pix))

    def toggle_think(self):
        self.thinking_expanded = not self.thinking_expanded
        self.think_frame.setVisible(self.thinking_expanded)
        self.update_toggle_icon()
        self.update_status_text(self.is_currently_thinking)

    def refresh_ui_text(self):
        """Called when language changes"""
        if not self.btn_think_toggle.isVisible() and len(self.full_text) < 20: 
             self.update_display_text(self.full_text)
        
        if self.btn_think_toggle.isVisible():
            self.update_status_text(self.is_currently_thinking)

    def update_status_text(self, is_thinking=False):
        self.is_currently_thinking = is_thinking
        duration_str = ""
        
        if self.think_duration is not None:
            duration_str = i18n.t("think_cost_pattern").format(self.think_duration)
        elif self.think_start_time is not None:
            elapsed = time.time() - self.think_start_time
            duration_str = i18n.t("think_duration_pattern").format(elapsed)
            
        if is_thinking:
            status = i18n.t("think_status_running")
            self.btn_think_toggle.setText(f" {status} {duration_str}")
        else:
            status = i18n.t("think_status_done")
            self.btn_think_toggle.setText(f" {status} {duration_str}")

    def update_text(self, new_text):
        self.full_text = new_text
        self.update_display_text(new_text)

    def update_display_text(self, text):
        if not text: return
        
        current_thinking_msg = i18n.t("msg_thinking")
        
        if text == current_thinking_msg or text == "思考中...":
            self.content_lbl.setText(f"<i style='color:#888'>{current_thinking_msg}</i>")
            self.btn_think_toggle.setVisible(False)
            self.think_frame.setVisible(False)
            return

        think_pattern = re.compile(r"<\s*think\s*>(.*?)(?:<\s*/\s*think\s*>|$)", re.DOTALL | re.IGNORECASE)
        match = think_pattern.search(text)

        think_content = ""
        main_content = text
        is_thinking = False

        if match:
            if self.think_duration is None and self.think_start_time is None: 
                self.think_start_time = time.time()
                
            think_content = match.group(1).strip()
            
            if re.search(r"<\s*/\s*think\s*>", text, re.IGNORECASE):
                main_content = think_pattern.sub("", text).strip()
                if self.think_duration is None and self.think_start_time:
                    self.think_duration = time.time() - self.think_start_time
            else:
                main_content = ""
                is_thinking = True

        if think_content:
            self.btn_think_toggle.setVisible(True)
            if self.thinking_expanded: self.think_frame.setVisible(True)
            safe_think = html.escape(think_content).replace("\n", "<br>")
            
            self.update_status_text(is_thinking)
            
            if is_thinking: safe_think += " <span style='color:#5aa9ff'>▌</span>"
            self.think_lbl.setText(safe_think)
        else:
            self.btn_think_toggle.setVisible(False)
            self.think_frame.setVisible(False)

        if main_content:
            self.content_lbl.setVisible(True)
            
            if HAS_MARKDOWN:
                html_content = markdown.markdown(main_content, extensions=['fenced_code', 'nl2br'])
                self.content_lbl.setTextFormat(Qt.TextFormat.RichText)
                self.content_lbl.setText(MARKDOWN_CSS + html_content)
            else:
                self.content_lbl.setTextFormat(Qt.TextFormat.MarkdownText)
                self.content_lbl.setText(main_content)
        else:
            self.content_lbl.setVisible(False)
            
    def copy_text(self):
        QApplication.clipboard().setText(self.full_text)