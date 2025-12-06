COLOR_BG_DARK = "#0b0f19"
COLOR_BG_PANEL = "#111827"
COLOR_BORDER = "#1f2937"
COLOR_TEXT_PRIMARY = "#e6e8ee"
COLOR_TEXT_SECONDARY = "#9ca3af"
COLOR_ACCENT = "#5aa9ff"
COLOR_ACCENT_HOVER = "#4a99ef"

COLOR_BUBBLE_USER = "#1e2842"
COLOR_BUBBLE_AI = "#2d3748"
COLOR_THINK_BG = "#1a1e24"
COLOR_THINK_BORDER = "#4b5563"

MAIN_STYLESHEET = f"""
QMainWindow {{ background-color: {COLOR_BG_DARK}; color: {COLOR_TEXT_PRIMARY}; }}
QWidget {{ font-family: 'Segoe UI', sans-serif; }}
"""


STYLE_BTN_PRIMARY = f"""
    QPushButton {{ 
        background-color: {COLOR_ACCENT}; 
        color: #000; 
        border-radius: 6px; 
        font-weight: bold; 
        padding: 8px; 
        font-size: 13px; 
        border: none;
    }}
    QPushButton:hover {{ background-color: {COLOR_ACCENT_HOVER}; }}
    QPushButton:disabled {{ background-color: #2c3e50; color: #555; }}
"""

STYLE_BTN_SECONDARY = f"""
    QPushButton {{ 
        background-color: {COLOR_BG_PANEL}; 
        border: 1px solid {COLOR_BORDER}; 
        border-radius: 4px; 
        color: {COLOR_TEXT_PRIMARY}; 
        padding: 5px; 
    }}
    QPushButton:hover {{ background-color: #374151; }}
"""

STYLE_BTN_DANGER = """
    QPushButton { background-color: #f08a5d; color: #000; border-radius: 6px; font-weight: bold; font-size: 14px; border: none; }
    QPushButton:hover { background-color: #e07a4d; }
"""

STYLE_BTN_DANGER_DARK = """
    QPushButton { background-color: #7f1d1d; border: 1px solid #991b1b; border-radius: 4px; color: #fee2e2; padding: 5px; }
    QPushButton:hover { background-color: #991b1b; }
"""

STYLE_BTN_GHOST = f"""
    QPushButton {{ 
        background: transparent; 
        border: 1px solid {COLOR_BORDER}; 
        border-radius: 6px; 
        color: {COLOR_TEXT_SECONDARY}; 
        padding: 6px 12px; 
        font-size: 12px; 
    }}
    QPushButton:checked {{ background-color: {COLOR_BORDER}; color: {COLOR_ACCENT}; border-color: {COLOR_ACCENT}; }}
    QPushButton:hover {{ background-color: {COLOR_BG_PANEL}; border-color: #4b5563; }}
"""

STYLE_BTN_LINK = """
    QPushButton { 
        background: transparent; 
        color: #6b7280; 
        border: none; 
        padding: 2px; 
        font-size: 11px; 
        text-align: right; 
    } 
    QPushButton:hover { color: #9ca3af; }
"""

STYLE_BTN_ICON_ONLY = """
    QPushButton { background: transparent; border: none; } 
    QPushButton:hover { background-color: #3e4f65; border-radius: 4px; }
"""

STYLE_BTN_THINK_TOGGLE = """
    QPushButton {
        background: transparent;
        text-align: left;
        color: #6b7280;
        font-size: 12px;
        border: none;
        font-weight: bold;
        padding: 4px 0;
    }
    QPushButton:hover { color: #9ca3af; }
"""


STYLE_COMBOBOX = f"""
    QComboBox {{ 
        background-color: {COLOR_BG_PANEL}; 
        border: 1px solid {COLOR_BORDER}; 
        border-radius: 4px; 
        padding: 4px; 
        color: {COLOR_TEXT_PRIMARY}; 
        min-height: 24px; 
    }}
    QComboBox:disabled {{ color: #555; }}
"""

STYLE_SPINBOX = f"""
    QAbstractSpinBox {{ 
        background-color: {COLOR_BG_PANEL}; 
        border: 1px solid {COLOR_BORDER}; 
        border-radius: 4px; 
        color: #f3f4f6; 
        padding: 2px 4px;
    }}
    QAbstractSpinBox:focus {{ border: 1px solid {COLOR_ACCENT}; }}
    QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ background: none; border: none; width: 0px; }}
"""

STYLE_INPUT_BOX = f"""
    QLineEdit {{ 
        background-color: #0e1525; 
        border: 1px solid {COLOR_BORDER}; 
        border-radius: 8px; 
        padding: 10px; 
        color: {COLOR_TEXT_PRIMARY}; 
        font-size: 14px; 
    }} 
    QLineEdit:focus {{ border: 1px solid {COLOR_ACCENT}; }}
"""

STYLE_TEXT_AREA = f"""
    QPlainTextEdit {{
        background-color: {COLOR_BG_PANEL};
        border: 1px solid #374151;
        border-radius: 6px;
        color: #f3f4f6;
        padding: 6px;
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
    }}
    QPlainTextEdit:focus {{ border: 1px solid {COLOR_ACCENT}; }}
"""

STYLE_CHECKBOX = f"""
    QCheckBox {{ color: {COLOR_TEXT_SECONDARY}; spacing: 8px; }} 
    QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 1px solid #4b5563; background: {COLOR_BG_PANEL}; }} 
    QCheckBox::indicator:checked {{ background-color: {COLOR_ACCENT}; border-color: {COLOR_ACCENT}; }}
"""

STYLE_SLIDER = f"""
    QSlider::groove:horizontal {{ height: 4px; background: #2d3748; border-radius: 2px; }}
    QSlider::handle:horizontal {{ background: {COLOR_ACCENT}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
    QSlider::handle:horizontal:hover {{ background: {COLOR_ACCENT_HOVER}; }}
"""

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
    QListWidget::item {{ padding: 8px; border-radius: 6px; color: {COLOR_TEXT_SECONDARY}; margin-bottom: 2px; }}
    QListWidget::item:selected {{ background-color: {COLOR_BORDER}; color: #fff; }}
    QListWidget::item:hover {{ background-color: {COLOR_BG_PANEL}; }}
"""

STYLE_SCROLL_AREA = f"""
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ width: 6px; background: transparent; }}
    QScrollBar::handle:vertical {{ background: #374151; border-radius: 3px; min-height: 20px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
"""

STYLE_PROGRESS_BAR = f"""
    QProgressBar {{ border: none; background-color: {COLOR_BORDER}; border-radius: 6px; }} 
    QProgressBar::chunk {{ background-color: {COLOR_ACCENT}; border-radius: 6px; }}
"""


STYLE_THINK_FRAME = f"""
    QFrame {{
        background-color: {COLOR_THINK_BG}; 
        border-left: 3px solid {COLOR_THINK_BORDER};
        border-radius: 4px;
        margin-bottom: 8px;
    }}
"""

STYLE_THINK_LABEL = "color: #9ca3af; font-size: 13px; font-family: 'Segoe UI', sans-serif;"

STYLE_CONTENT_BUBBLE_BASE = """
    QLabel {
        border-radius: 12px;
        padding: 12px;
        font-size: 14px;
        line-height: 1.5;
        color: #ffffff;
    }
"""

MARKDOWN_CSS = f"""
<style>
pre {{ 
    background-color: #12151b; 
    color: #dcdfe4; 
    padding: 10px; 
    border-radius: 6px; 
    border: 1px solid #2b323b; 
    font-family: Consolas, monospace;
}}
code {{ color: #dcdfe4; }}
h1, h2, h3 {{ color: {COLOR_ACCENT}; font-weight: bold; margin-top: 10px; }}
strong {{ color: #f0f0f0; }}
p {{ margin-bottom: 8px; }}
a {{ color: {COLOR_ACCENT}; text-decoration: none; }}
</style>
"""


STYLE_CHAT_INPUT_BAR = f"background-color: {COLOR_BG_DARK}; border-top: 1px solid {COLOR_BORDER};"


STYLE_LABEL_DIM = "color: #6b7280; font-size: 11px;"
STYLE_LABEL_NORMAL = "color: #9ca3af; font-size: 12px; margin-bottom: 2px;"
STYLE_LABEL_TITLE = f"font-weight: bold; font-size: 16px; color: {COLOR_ACCENT}; margin-bottom: 5px;"