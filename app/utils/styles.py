MAIN_STYLESHEET = """
QMainWindow { background-color: #0b0f19; color: #e6e8ee; }
QTextEdit { background-color: #0e1525; border: 1px solid #1e2842; color: #e6e8ee; border-radius: 8px; padding: 8px; }
QLineEdit { background-color: #0b1226; border: 1px solid #1e2842; color: #e6e8ee; border-radius: 8px; padding: 8px; }
QPushButton { background-color: #2c3e50; color: #fff; border-radius: 6px; padding: 6px 12px; border: 1px solid #3e4f65; }
QPushButton:hover { background-color: #3e4f65; }
QPushButton#PrimaryBtn { background-color: #5aa9ff; color: #000; border: none; font-weight: bold; }
QPushButton#PrimaryBtn:hover { background-color: #4a99ef; }
QPushButton#PrimaryBtn:disabled { background-color: #2c3e50; color: #7f8c8d; }
QPushButton#StopBtn { background-color: #f08a5d; color: #000; border: none; font-weight: bold; }
QListWidget { background-color: #0b0f19; border: none; outline: none; }
QListWidget::item { padding: 8px; border-radius: 6px; color: #99a3b3; }
QListWidget::item:selected { background-color: #1e2842; color: #fff; }
QListWidget::item:hover { background-color: #151e32; }
QComboBox { background-color: #121a31; color: #cfe1ff; border: 1px solid #1e2842; border-radius: 4px; padding: 4px; }
QLabel { color: #99a3b3; }
QGroupBox { border: 1px solid #1e2842; border-radius: 8px; margin-top: 10px; font-weight: bold; color: #5aa9ff; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
QProgressBar { border: 1px solid #1e2842; border-radius: 4px; text-align: center; color: #fff; background-color: #0b1226; }
QProgressBar::chunk { background-color: #5aa9ff; border-radius: 4px; }
"""