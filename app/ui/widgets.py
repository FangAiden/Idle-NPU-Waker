from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QSlider, QSpinBox, 
                             QDoubleSpinBox, QPlainTextEdit)
from PyQt6.QtCore import Qt
from app.utils.styles import STYLE_SLIDER, STYLE_SPINBOX

class SliderControl(QWidget):
    def __init__(self, dtype, min_val, max_val, step, default_val):
        super().__init__()
        self.dtype = dtype
        self.step = step
        self.factor = 1.0 / step if dtype == "float" else 1
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(int(min_val * self.factor), int(max_val * self.factor))
        self.slider.setValue(int(default_val * self.factor))
        self.slider.setStyleSheet(STYLE_SLIDER)
        
        if dtype == "float":
            self.spinner = QDoubleSpinBox()
            self.spinner.setRange(min_val, max_val)
            self.spinner.setSingleStep(step)
            self.spinner.setValue(default_val)
            self.spinner.setDecimals(2 if step < 0.1 else 1)
        else:
            self.spinner = QSpinBox()
            self.spinner.setRange(int(min_val), int(max_val))
            self.spinner.setSingleStep(int(step))
            self.spinner.setValue(int(default_val))
            
        self.spinner.setFixedWidth(75)
        self.spinner.setFixedHeight(28)
        self.spinner.setStyleSheet(STYLE_SPINBOX)

        self.slider.valueChanged.connect(self._on_slider_change)
        self.spinner.valueChanged.connect(self._on_spinner_change)

        layout.addWidget(self.slider)
        layout.addWidget(self.spinner)

    def _on_slider_change(self, val):
        self.spinner.blockSignals(True)
        new_val = val / self.factor if self.dtype == "float" else val
        self.spinner.setValue(new_val)
        self.spinner.blockSignals(False)

    def _on_spinner_change(self, val):
        self.slider.blockSignals(True)
        new_val = int(val * self.factor)
        self.slider.setValue(new_val)
        self.slider.blockSignals(False)

    def value(self):
        return self.spinner.value()

    def setValue(self, val):
        self.spinner.setValue(val)


class TextAreaControl(QPlainTextEdit):
    def __init__(self, default_text=""):
        super().__init__()
        self.setPlainText(str(default_text))
        self.setFixedHeight(80)
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #111827;
                border: 1px solid #374151;
                border-radius: 6px;
                color: #f3f4f6;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QPlainTextEdit:focus { border: 1px solid #5aa9ff; }
        """)

    def value(self):
        return self.toPlainText()

    def setValue(self, val):
        self.setPlainText(str(val))