import re
import html
import time
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                             QPushButton, QApplication, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QDesktopServices, QTransform
from app.ui.resources import AI_AVATAR_SVG, USER_AVATAR_SVG, CHEVRON_ICON_SVG
from app.ui.widgets import Toast
from app.core.i18n import i18n
from app.utils.styles import (
    STYLE_BTN_THINK_TOGGLE, STYLE_THINK_FRAME, STYLE_THINK_LABEL,
    STYLE_CONTENT_BUBBLE_BASE, STYLE_BTN_LINK, MARKDOWN_CSS,
    COLOR_BUBBLE_USER, COLOR_BUBBLE_AI,
    RATIO_BUBBLE_AI, RATIO_BUBBLE_USER
)

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

try:
    import pygments  # noqa: F401
    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False

class MessageBubble(QWidget):
    sig_edit_requested = pyqtSignal(int)
    sig_retry_requested = pyqtSignal(int)

    def __init__(self, text, is_user=False, think_duration=None, message_index=None, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.full_text = text
        self.message_index = message_index
        self.thinking_expanded = True
        self._code_blocks_main = []
        self._code_blocks_think = []
        
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
        self.think_lbl.setOpenExternalLinks(True)
        self.think_lbl.linkActivated.connect(lambda url: self.open_link(url, target="think"))
        self.think_lbl.setStyleSheet(STYLE_THINK_LABEL)
        think_layout.addWidget(self.think_lbl)
        self.content_layout.addWidget(self.think_frame)

        self.content_lbl = QLabel()
        self.content_lbl.setWordWrap(True)
        self.content_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.content_lbl.setOpenExternalLinks(True)
        self.content_lbl.linkActivated.connect(lambda url: self.open_link(url, target="main"))
        
        bg_color = COLOR_BUBBLE_USER if self.is_user else COLOR_BUBBLE_AI
        self.content_lbl.setStyleSheet(STYLE_CONTENT_BUBBLE_BASE + f"QLabel {{ background-color: {bg_color}; }}")
        self.content_layout.addWidget(self.content_lbl)

        self.actions_container = QWidget()
        actions_layout = QHBoxLayout(self.actions_container)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)

        self.btn_copy = QPushButton()
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setStyleSheet(STYLE_BTN_LINK)
        self.btn_copy.clicked.connect(self.copy_text)

        self.btn_edit = QPushButton()
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.setStyleSheet(STYLE_BTN_LINK)
        self.btn_edit.clicked.connect(self._on_edit_clicked)

        self.btn_retry = QPushButton()
        self.btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_retry.setStyleSheet(STYLE_BTN_LINK)
        self.btn_retry.clicked.connect(self._on_retry_clicked)

        if self.is_user:
            actions_layout.addStretch()
            actions_layout.addWidget(self.btn_edit)
            actions_layout.addWidget(self.btn_copy)
        else:
            actions_layout.addWidget(self.btn_copy)
            actions_layout.addWidget(self.btn_retry)
            actions_layout.addStretch()

        self.content_layout.addWidget(self.actions_container)

        if self.is_user:
            layout.addStretch()
            layout.addWidget(self.content_container)
            layout.addWidget(self.avatar_lbl, alignment=Qt.AlignmentFlag.AlignTop)
        else:
            layout.addWidget(self.avatar_lbl, alignment=Qt.AlignmentFlag.AlignTop)
            layout.addWidget(self.content_container)
            layout.addStretch()

        self.update_display_text(self.full_text)
        self.update_toggle_icon()
        self.update_action_texts()
        self.set_message_index(self.message_index)

    def adjust_width(self, parent_width):
        """根据父容器宽度动态调整气泡最大宽度"""
        ai_target_width = int(parent_width * RATIO_BUBBLE_AI)
        
        if self.is_user:
            user_target_width = int(ai_target_width * RATIO_BUBBLE_USER)
            self.content_container.setFixedWidth(user_target_width)
        else:
            self.content_container.setFixedWidth(ai_target_width)

    def open_link(self, url, target="main"):
        url_str = url.toString() if isinstance(url, QUrl) else str(url)
        if url_str.startswith("copy://"):
            try:
                idx = int(url_str.rsplit("/", 1)[-1])
            except ValueError:
                return
            if target == "think":
                blocks = self._code_blocks_think
            else:
                blocks = self._code_blocks_main
            if 0 <= idx < len(blocks):
                QApplication.clipboard().setText(blocks[idx])
                toast = Toast(i18n.t("msg_copied", "Copied successfully"), self.window())
                toast.show_notification()
            return
        QDesktopServices.openUrl(QUrl(url_str))

    def _extract_code_blocks(self, text):
        if not text:
            return []
        pattern = re.compile(r"```[^\n]*\n([\s\S]*?)```", re.MULTILINE)
        return [match.group(1).strip("\n") for match in pattern.finditer(text)]

    def _inject_copy_links(self, html_text, context="main"):
        copy_label = html.escape(i18n.t("btn_copy", "Copy"))
        blocks = self._code_blocks_think if context == "think" else self._code_blocks_main

        def wrap_blocks(pattern, source):
            index = 0
            def repl(match):
                nonlocal index
                block_html = match.group(1)
                link = f"<a href=\"copy://{context}/{index}\" class=\"code-copy\">{copy_label}</a>"
                index += 1
                return f"<div class=\"code-block\">{block_html}<div class=\"code-tools\">{link}</div></div>"
            return pattern.sub(repl, source)

        if "codehilite" in html_text:
            pattern = re.compile(r"(<div class=\"codehilite\">[\s\S]*?</div>)", re.MULTILINE)
            return wrap_blocks(pattern, html_text)

        pattern = re.compile(r"(<pre>[\s\S]*?</pre>)", re.MULTILINE)
        return wrap_blocks(pattern, html_text)

    def _render_markdown(self, text, context="main"):
        if not HAS_MARKDOWN:
            safe_text = html.escape(text).replace("\n", "<br>")
            return safe_text

        if context == "think":
            self._code_blocks_think = self._extract_code_blocks(text)
        else:
            self._code_blocks_main = self._extract_code_blocks(text)

        extensions = ["fenced_code", "nl2br"]
        extension_configs = {}
        if HAS_PYGMENTS:
            extensions.append("codehilite")
            extension_configs["codehilite"] = {
                "guess_lang": False,
                "noclasses": True,
                "pygments_style": "monokai"
            }

        html_content = markdown.markdown(text, extensions=extensions, extension_configs=extension_configs)
        html_content = self._inject_copy_links(html_content, context=context)
        return html_content

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
        self.update_action_texts()
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

    def set_message_index(self, index):
        self.message_index = index
        has_index = index is not None and index >= 0
        if self.is_user:
            self.btn_edit.setEnabled(has_index)
        else:
            self.btn_retry.setEnabled(has_index)

    def update_action_texts(self):
        if self.is_user:
            self.btn_edit.setText(i18n.t("btn_edit", "Edit"))
            self.btn_copy.setText(i18n.t("btn_copy", "Copy"))
        else:
            self.btn_copy.setText(i18n.t("btn_copy", "Copy"))
            self.btn_retry.setText(i18n.t("btn_retry", "Retry"))

    def _on_edit_clicked(self):
        if self.message_index is None:
            return
        self.sig_edit_requested.emit(self.message_index)

    def _on_retry_clicked(self):
        if self.message_index is None:
            return
        self.sig_retry_requested.emit(self.message_index)

    def update_display_text(self, text):
        if not text: return
        
        current_thinking_msg = i18n.t("msg_thinking")
        
        if self.is_user:
            self.btn_think_toggle.setVisible(False)
            self.think_frame.setVisible(False)
            self.content_lbl.setVisible(True)
            self.content_lbl.setTextFormat(Qt.TextFormat.PlainText)
            self.content_lbl.setText(text)
            self.actions_container.setVisible(True)
            return

        if text == current_thinking_msg or text == "思考中...":
            self.content_lbl.setText(f"<i style='color:#888'>{current_thinking_msg}</i>")
            self.btn_think_toggle.setVisible(False)
            self.think_frame.setVisible(False)
            self.actions_container.setVisible(False)
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

            self.update_status_text(is_thinking)

            if HAS_MARKDOWN:
                html_content = self._render_markdown(think_content, context="think")
                self.think_lbl.setTextFormat(Qt.TextFormat.RichText)
                self.think_lbl.setText(MARKDOWN_CSS + html_content)
            else:
                safe_think = html.escape(think_content).replace("\n", "<br>")
                self.think_lbl.setTextFormat(Qt.TextFormat.RichText)
                self.think_lbl.setText(safe_think)

        else:
            self.btn_think_toggle.setVisible(False)
            self.think_frame.setVisible(False)

        if main_content:
            self.content_lbl.setVisible(True)
            
            if HAS_MARKDOWN:
                html_content = self._render_markdown(main_content, context="main")
                self.content_lbl.setTextFormat(Qt.TextFormat.RichText)
                self.content_lbl.setText(MARKDOWN_CSS + html_content)
            else:
                self.content_lbl.setTextFormat(Qt.TextFormat.MarkdownText)
                self.content_lbl.setText(main_content)
            self.actions_container.setVisible(True)
        else:
            self.content_lbl.setVisible(False)
            self.actions_container.setVisible(False)
            
    def copy_text(self):
        QApplication.clipboard().setText(self.full_text)
        toast = Toast(i18n.t("msg_copied", "Copied successfully"), self.window())
        toast.show_notification()
