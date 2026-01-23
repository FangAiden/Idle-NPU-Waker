"""
统一的样式定义文件
包含了颜色常量和所有 Qt 控件的 QSS 样式表。
"""

# ================= 颜色定义 =================
COLOR_BG_DARK = "#212121"
COLOR_BG_PANEL = "#171717"
COLOR_BG_TERTIARY = "#2f2f2f"
COLOR_BG_HOVER = "#3a3a3a"
COLOR_BORDER = "#444"
COLOR_TEXT_PRIMARY = "#ececec"
COLOR_TEXT_SECONDARY = "#b4b4b4"
COLOR_TEXT_MUTED = "#8e8e8e"
COLOR_ACCENT = "#10a37f"
COLOR_ACCENT_HOVER = "#0d8c6d"

COLOR_BUBBLE_USER = "#2f2f2f"
COLOR_BUBBLE_AI = "transparent"
COLOR_THINK_BG = "#2f2f2f"
COLOR_THINK_BORDER = "#10a37f"

# ================= 尺寸比例定义 =================
RATIO_BUBBLE_AI = 0.90
RATIO_BUBBLE_USER = 0.60

# ================= 全局样式 =================
MAIN_STYLESHEET = f"""
QMainWindow {{ background-color: {COLOR_BG_DARK}; color: {COLOR_TEXT_PRIMARY}; }}
QWidget {{ font-family: 'Segoe UI', sans-serif; }}
"""

# ================= 按钮样式 =================
STYLE_BTN_PRIMARY = f"""
    QPushButton {{ 
        background-color: {COLOR_ACCENT};
        color: #ffffff;
        border-radius: 8px;
        font-weight: 600;
        padding: 8px 12px;
        font-size: 13px;
        border: none;
    }}
    QPushButton:hover {{ background-color: {COLOR_ACCENT_HOVER}; }}
    QPushButton:disabled {{ background-color: #2a2a2a; color: #666; }}
"""

STYLE_BTN_CHAT = f"""
    QPushButton {{
        background-color: transparent;
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        color: {COLOR_TEXT_PRIMARY};
        padding: 10px 12px;
        font-size: 13px;
        font-weight: 600;
        text-align: left;
    }}
    QPushButton:hover {{
        background-color: {COLOR_BG_TERTIARY};
    }}
"""

STYLE_BTN_SECONDARY = f"""
    QPushButton {{ 
        background-color: {COLOR_BG_TERTIARY};
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        color: {COLOR_TEXT_PRIMARY};
        padding: 6px 10px;
    }}
    QPushButton:hover {{ background-color: {COLOR_BG_HOVER}; }}
"""

STYLE_BTN_DANGER = """
    QPushButton { background-color: #ef4444; color: #fff; border-radius: 8px; font-weight: 600; font-size: 13px; border: none; padding: 8px 12px; }
    QPushButton:hover { background-color: #dc2626; }
"""

STYLE_BTN_DANGER_DARK = """
    QPushButton { background-color: #7f1d1d; border: 1px solid #991b1b; border-radius: 8px; color: #fee2e2; padding: 6px 10px; }
    QPushButton:hover { background-color: #991b1b; }
"""

STYLE_BTN_GHOST = f"""
    QPushButton {{ 
        background: transparent; 
        border: 1px solid {COLOR_BORDER}; 
        border-radius: 8px; 
        color: {COLOR_TEXT_SECONDARY}; 
        padding: 8px 12px; 
        font-size: 12px;
    }}
    QPushButton:checked {{ background-color: {COLOR_BG_TERTIARY}; color: {COLOR_ACCENT}; border-color: {COLOR_ACCENT}; }}
    QPushButton:hover {{ background-color: {COLOR_BG_TERTIARY}; border-color: {COLOR_ACCENT}; }}
"""

STYLE_BTN_LINK = """
    QPushButton { 
        background: transparent; 
        color: #8e8e8e; 
        border: none; 
        padding: 2px; 
        font-size: 11px; 
        text-align: right; 
    } 
    QPushButton:hover { color: #ececec; }
"""

STYLE_BTN_ICON_ONLY = """
    QPushButton { background: transparent; border: none; } 
    QPushButton:hover { background-color: #3e4f65; border-radius: 4px; }
"""

STYLE_BTN_THINK_TOGGLE = """
    QPushButton {
        background: transparent;
        text-align: left;
        color: #8e8e8e;
        font-size: 12px;
        border: none;
        font-weight: 600;
        padding: 4px 0;
    }
    QPushButton:hover { color: #ececec; }
"""

STYLE_BTN_SESSION_MORE = """
    QPushButton { background: transparent; border: none; border-radius: 4px; }
    QPushButton:hover { background-color: #3a3a3a; }
"""

STYLE_BTN_SIDEBAR_TOGGLE = f"""
    QPushButton {{
        background: transparent;
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        padding: 6px;
    }}
    QPushButton:hover {{
        background-color: {COLOR_BG_TERTIARY};
        border-color: {COLOR_ACCENT};
    }}
"""

STYLE_BTN_TEMP_CHAT = f"""
    QPushButton {{
        background-color: transparent;
        border: 1px dashed {COLOR_BORDER};
        border-radius: 8px;
        font-weight: 600;
        padding: 8px;
        font-size: 13px;
        color: {COLOR_TEXT_SECONDARY};
    }}
    QPushButton:hover {{
        background-color: {COLOR_BG_TERTIARY};
        border-color: {COLOR_ACCENT};
        color: {COLOR_ACCENT};
    }}
"""

STYLE_TEMP_SESSION_ITEM = f"""
    QWidget {{
        background: transparent;
    }}
    QLabel {{
        color: {COLOR_TEXT_SECONDARY};
        font-style: italic;
    }}
"""

STYLE_BTN_SCROLL_BOTTOM = f"""
    QPushButton {{
        background-color: {COLOR_BG_TERTIARY};
        border: 1px solid {COLOR_BORDER};
        border-radius: 20px;
        color: {COLOR_TEXT_SECONDARY};
        padding: 0px;
    }}
    QPushButton:hover {{
        background-color: {COLOR_BG_HOVER};
        color: {COLOR_ACCENT};
        border-color: {COLOR_ACCENT};
    }}
"""

# ================= 输入与控制控件样式 =================
STYLE_COMBOBOX = f"""
    QComboBox {{ 
        background-color: {COLOR_BG_TERTIARY};
        border: 1px solid {COLOR_BORDER}; 
        border-radius: 8px; 
        padding: 6px 8px; 
        color: {COLOR_TEXT_PRIMARY}; 
        min-height: 28px; 
    }}
    QComboBox:disabled {{ color: #666; }}
"""

STYLE_SPINBOX = f"""
    QAbstractSpinBox {{ 
        background-color: {COLOR_BG_TERTIARY};
        border: 1px solid {COLOR_BORDER}; 
        border-radius: 8px; 
        color: {COLOR_TEXT_PRIMARY};
        padding: 4px 6px;
    }}
    QAbstractSpinBox:focus {{ border: 1px solid {COLOR_ACCENT}; }}
    QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ background: none; border: none; width: 0px; }}
"""

STYLE_INPUT_BOX = f"""
    QLineEdit {{ 
        background-color: {COLOR_BG_TERTIARY};
        border: 1px solid {COLOR_BORDER}; 
        border-radius: 12px; 
        padding: 10px 12px; 
        color: {COLOR_TEXT_PRIMARY}; 
        font-size: 14px; 
    }} 
    QLineEdit:focus {{ border: 1px solid {COLOR_ACCENT}; }}
"""

STYLE_CHAT_INPUT_BAR = f"background-color: {COLOR_BG_DARK}; border-top: 1px solid {COLOR_BORDER};"

STYLE_TEXT_AREA = f"""
    QPlainTextEdit {{
        background-color: {COLOR_BG_TERTIARY};
        border: 1px solid {COLOR_BORDER};
        border-radius: 8px;
        color: {COLOR_TEXT_PRIMARY};
        padding: 6px;
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
    }}
    QPlainTextEdit:focus {{ border: 1px solid {COLOR_ACCENT}; }}
"""

STYLE_CHECKBOX = f"""
    QCheckBox {{ color: {COLOR_TEXT_SECONDARY}; spacing: 8px; }} 
    QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 1px solid {COLOR_BORDER}; background: {COLOR_BG_TERTIARY}; }} 
    QCheckBox::indicator:checked {{ background-color: {COLOR_ACCENT}; border-color: {COLOR_ACCENT}; }}
"""

STYLE_SLIDER = f"""
    QSlider::groove:horizontal {{ height: 4px; background: {COLOR_BORDER}; border-radius: 2px; }}
    QSlider::handle:horizontal {{ background: {COLOR_ACCENT}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
    QSlider::handle:horizontal:hover {{ background: {COLOR_ACCENT_HOVER}; }}
"""

# ================= 容器与布局样式 =================
STYLE_GROUP_BOX = f"""
    QGroupBox {{ 
        border: 1px solid {COLOR_BORDER}; 
        border-radius: 8px; 
        margin-top: 10px; 
        padding-top: 10px; 
        font-weight: bold; 
        color: {COLOR_TEXT_PRIMARY}; 
    }} 
    QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}
"""

STYLE_LIST_WIDGET = f"""
    QListWidget {{ background: transparent; border: none; outline: none; }}
    QListWidget::item {{ padding: 8px; border-radius: 8px; color: {COLOR_TEXT_SECONDARY}; margin-bottom: 2px; }}
    QListWidget::item:selected {{ background-color: {COLOR_BG_TERTIARY}; color: {COLOR_TEXT_PRIMARY}; }}
    QListWidget::item:hover {{ background-color: {COLOR_BG_TERTIARY}; }}
"""

STYLE_SCROLL_AREA = f"""
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ width: 6px; background: transparent; }}
    QScrollBar::handle:vertical {{ background: {COLOR_BORDER}; border-radius: 3px; min-height: 20px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
"""

STYLE_THINK_FRAME = f"""
    QFrame {{
        background-color: {COLOR_THINK_BG}; 
        border-left: 3px solid {COLOR_THINK_BORDER};
        border-radius: 6px;
        margin-bottom: 8px;
    }}
"""

STYLE_PROGRESS_BAR = f"""
    QProgressBar {{ border: none; background-color: {COLOR_BORDER}; border-radius: 999px; }} 
    QProgressBar::chunk {{ background-color: {COLOR_ACCENT}; border-radius: 999px; }}
"""

STYLE_SPLITTER = f"QSplitter::handle {{ background-color: {COLOR_BG_TERTIARY}; }}"
STYLE_SIDEBAR_BOTTOM_BAR = f"background-color: {COLOR_BG_PANEL}; border-top: 1px solid {COLOR_BORDER};"
STYLE_TOP_BAR = f"background-color: {COLOR_BG_PANEL}; border-bottom: 1px solid {COLOR_BORDER};"
STYLE_STATUS_DOT_IDLE = f"background-color: {COLOR_TEXT_MUTED}; border-radius: 4px;"
STYLE_STATUS_DOT_LOADING = "background-color: #f59e0b; border-radius: 4px;"
STYLE_STATUS_DOT_READY = f"background-color: {COLOR_ACCENT}; border-radius: 4px;"
STYLE_STATUS_DOT_WARNING = "background-color: #fbbf24; border-radius: 4px;"

STYLE_MENU_DARK = """
    QMenu { background-color: #171717; color: #ececec; border: 1px solid #444; }
    QMenu::item { padding: 6px 20px; }
    QMenu::item:selected { background-color: #2f2f2f; }
"""

# ================= 标签与文本样式 =================
STYLE_THINK_LABEL = "color: #b4b4b4; font-size: 13px; font-family: 'Segoe UI', sans-serif;"

STYLE_CONTENT_BUBBLE_BASE = """
    QLabel {
        border-radius: 12px;
        padding: 12px;
        font-size: 14px;
        line-height: 1.6;
        color: #ececec;
    }
"""

STYLE_LABEL_DIM = "color: #8e8e8e; font-size: 11px;"
STYLE_LABEL_NORMAL = "color: #b4b4b4; font-size: 12px; margin-bottom: 2px;"
STYLE_LABEL_TITLE = f"font-weight: 600; font-size: 16px; color: {COLOR_ACCENT}; margin-bottom: 5px;"
STYLE_LABEL_SESSION_TITLE = "background: transparent; color: #ececec; font-size: 13px;"
STYLE_LABEL_STATS = "color: #8e8e8e; font-size: 11px; font-family: Consolas, monospace;"
STYLE_LABEL_STATUS_SMALL = "font-size: 11px; color: #8e8e8e;"
STYLE_LABEL_SETTING_ITEM = "color: #ececec; font-size: 13px; font-weight: 500;"

# ================= Toast 样式 =================
STYLE_TOAST = """
    QLabel {
        background-color: rgba(23, 23, 23, 230);
        border: 1px solid #444;
        color: #ececec;
        padding: 10px 20px;
        border-radius: 8px;
        font-size: 13px;
        font-family: 'Segoe UI', sans-serif;
        font-weight: 600;
    }
"""

# ================= Markdown 渲染样式 =================
MARKDOWN_CSS = f"""
<style>
pre {{ 
    background-color: #171717; 
    color: #ececec; 
    padding: 10px; 
    border-radius: 8px; 
    border: 1px solid #444; 
    font-family: Consolas, monospace;
}}
code {{ color: #ececec; }}
.code-block {{
    margin: 8px 0;
}}
.code-tools {{
    text-align: right;
    margin-top: 4px;
}}
.code-copy {{
    display: inline-block;
    color: #b4b4b4;
    border: 1px solid #444;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    text-decoration: none;
}}
h1, h2, h3 {{ color: {COLOR_ACCENT}; font-weight: 600; margin-top: 10px; }}
strong {{ color: #ffffff; }}
p {{ margin-bottom: 8px; }}
a {{ color: {COLOR_ACCENT}; text-decoration: none; }}
</style>
"""
