from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QSlider, QSpinBox, 
                             QDoubleSpinBox, QPlainTextEdit, QComboBox, QLabel, QApplication)
from PyQt6.QtCore import Qt, QTimer
from app.utils.styles import (
    STYLE_SLIDER, STYLE_SPINBOX, STYLE_TEXT_AREA, STYLE_COMBOBOX, STYLE_TOAST
)

class Toast(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        self.setStyleSheet(STYLE_TOAST)
        
        self.setText(text)
        self.adjustSize()
        
        QTimer.singleShot(2000, self.close)

    def show_notification(self):
        """显示在父窗口的右上角"""
        if not self.parent():
            self.show()
            return

        parent_rect = self.parent().rect()
        
        margin_right = 30
        margin_top = 40
        
        x = parent_rect.width() - self.width() - margin_right
        y = margin_top
        
        self.move(x, y)
        self.show()
        self.raise_()

class NoScrollComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()

class NoScrollSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()

class NoScrollDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event):
        event.ignore()

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
            self.spinner = NoScrollDoubleSpinBox()
            self.spinner.setRange(min_val, max_val)
            self.spinner.setSingleStep(step)
            self.spinner.setValue(default_val)
            self.spinner.setDecimals(2 if step < 0.1 else 1)
        else:
            self.spinner = NoScrollSpinBox()
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
        self.setStyleSheet(STYLE_TEXT_AREA)

    def value(self):
        return self.toPlainText()

    def setValue(self, val):
        self.setPlainText(str(val))