from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, 
                             QCheckBox, QGroupBox)
from PyQt6.QtCore import Qt
from app.config import CONFIG_GROUPS
from app.model_configs import MODEL_SPECIFIC_CONFIGS 
from app.core.i18n import i18n
from app.ui.widgets import SliderControl, TextAreaControl, NoScrollSpinBox, NoScrollDoubleSpinBox
from app.utils.config_loader import resolve_supported_setting_keys
from app.utils.styles import (
    STYLE_SCROLL_AREA, STYLE_CHECKBOX, STYLE_SPINBOX, STYLE_LABEL_TITLE, 
    STYLE_GROUP_BOX, STYLE_LABEL_SETTING_ITEM
)

class ModelSettingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_widgets = {}
        self.config_groups = CONFIG_GROUPS
        self.supported_keys = None
        self.all_setting_keys = set()
        for group in CONFIG_GROUPS:
            self.all_setting_keys.update(group.get("options", {}).keys())
        self.init_ui()
        i18n.language_changed.connect(self.update_texts)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet(STYLE_LABEL_TITLE)
        layout.addWidget(self.lbl_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(STYLE_SCROLL_AREA)
        
        scroll_content = QWidget()
        self.container_layout = QVBoxLayout(scroll_content)
        self.container_layout.setContentsMargins(10, 10, 10, 10)
        self.container_layout.setSpacing(25)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.build_form()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
        
        self.update_texts()

    def build_form(self):
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.config_widgets.clear()

        for group_def in self.config_groups:
            group_box = QGroupBox()
            group_box.setProperty("i18n_key", group_def["title_key"])
            group_box.setTitle(i18n.t(group_def["title_key"]))
            group_box.setStyleSheet(STYLE_GROUP_BOX)
            
            group_layout = QVBoxLayout(group_box)
            group_layout.setSpacing(15)
            group_layout.setContentsMargins(15, 20, 15, 15)

            for key, meta in group_def["options"].items():
                item_container = QWidget()
                item_layout = QVBoxLayout(item_container)
                item_layout.setContentsMargins(0, 0, 0, 0)
                item_layout.setSpacing(6)

                label = QLabel()
                label.setProperty("i18n_key", meta["label_key"])
                label.setText(i18n.t(meta["label_key"])) 
                label.setStyleSheet(STYLE_LABEL_SETTING_ITEM)
                item_layout.addWidget(label)
                
                widget = self._create_widget(meta)
                
                if widget:
                    widget.setProperty("default_val", meta["default"])
                    self.config_widgets[key] = widget
                    item_layout.addWidget(widget)
                    group_layout.addWidget(item_container)
            
            self.container_layout.addWidget(group_box)

    def _filter_groups(self, allowed_keys):
        if not allowed_keys:
            return CONFIG_GROUPS
        filtered = []
        for group_def in CONFIG_GROUPS:
            options = {
                key: meta
                for key, meta in group_def.get("options", {}).items()
                if key in allowed_keys
            }
            if options:
                filtered.append({
                    "title_key": group_def["title_key"],
                    "options": options
                })
        return filtered

    def apply_supported_settings(self, model_name, model_path):
        allowed = resolve_supported_setting_keys(
            model_name=model_name,
            model_path=model_path,
            all_setting_keys=self.all_setting_keys
        )
        allowed = set(allowed) if allowed else set(self.all_setting_keys)
        if allowed == self.supported_keys:
            return
        self.supported_keys = allowed
        self.config_groups = self._filter_groups(allowed)
        self.build_form()
        self.update_texts()

    def _create_widget(self, meta):
        w_type = meta.get("widget", "spin")
        widget = None
        
        if meta["type"] == "bool":
            widget = QCheckBox()
            widget.setChecked(meta["default"])
            widget.setText(i18n.t("opt_enabled", "Enabled"))
            widget.setStyleSheet(STYLE_CHECKBOX)
        elif w_type == "slider":
            widget = SliderControl(meta["type"], meta["min"], meta["max"], meta["step"], meta["default"])
        elif w_type == "textarea":
            widget = TextAreaControl(meta["default"])
        else:
            if meta["type"] == "int":
                widget = NoScrollSpinBox()
                widget.setRange(meta["min"], meta["max"])
                widget.setSingleStep(meta["step"])
                widget.setValue(meta["default"])
            else:
                widget = NoScrollDoubleSpinBox()
                widget.setRange(meta["min"], meta["max"])
                widget.setSingleStep(meta["step"])
                widget.setValue(meta["default"])
            widget.setFixedHeight(32)
            widget.setStyleSheet(STYLE_SPINBOX)
        return widget

    def apply_preset(self, model_name):
        self.block_signals_all(True)
        for widget in self.config_widgets.values():
            val = widget.property("default_val")
            self._set_widget_value(widget, val)
        
        target_cfg = {}
        for mid, cfg in MODEL_SPECIFIC_CONFIGS.items():
            if Path(mid).name == model_name or mid in model_name:
                target_cfg = cfg
                break
        
        if target_cfg:
            for key_or_group, val_or_dict in target_cfg.items():
                if isinstance(val_or_dict, dict):
                    for sub_key, sub_val in val_or_dict.items():
                        if sub_key in self.config_widgets:
                            self._set_widget_value(self.config_widgets[sub_key], sub_val)
                elif key_or_group in self.config_widgets:
                    self._set_widget_value(self.config_widgets[key_or_group], val_or_dict)
                    
        self.block_signals_all(False)

    def apply_dynamic_config(self, config_data):
        self.block_signals_all(True)
        
        mapping = {
            "temperature": "temperature",
            "top_p": "top_p",
            "top_k": "top_k",
            "repetition_penalty": "repetition_penalty",
            "do_sample": "do_sample",
            "max_new_tokens": "max_new_tokens"
        }

        for json_key, widget_key in mapping.items():
            if json_key in config_data and widget_key in self.config_widgets:
                val = config_data[json_key]
                if widget_key == "top_k": val = int(val)
                elif widget_key == "max_new_tokens": val = int(val)
                
                self._set_widget_value(self.config_widgets[widget_key], val)

        if "model_max_length" in config_data:
            max_len = config_data["model_max_length"]
            if "max_new_tokens" in self.config_widgets:
                widget = self.config_widgets["max_new_tokens"]
                safe_max = min(max_len, 8192) 
                if isinstance(widget, SliderControl):
                    widget.slider.setMaximum(int(safe_max))
                    widget.spinner.setMaximum(int(safe_max))

        self.block_signals_all(False)

    def _set_widget_value(self, widget, val):
        if isinstance(widget, SliderControl):
            widget.setValue(val)
        elif isinstance(widget, TextAreaControl):
            widget.setValue(str(val))
        elif isinstance(widget, (NoScrollSpinBox, NoScrollDoubleSpinBox)):
            widget.setValue(val)
        elif isinstance(widget, QCheckBox):
            widget.setChecked(val)

    def get_config(self):
        cfg = {}
        for key, widget in self.config_widgets.items():
            if isinstance(widget, (SliderControl, TextAreaControl)):
                cfg[key] = widget.value()
            elif isinstance(widget, (NoScrollSpinBox, NoScrollDoubleSpinBox)):
                cfg[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                cfg[key] = widget.isChecked()
        return cfg

    def block_signals_all(self, block):
        for w in self.config_widgets.values():
            w.blockSignals(block)

    def update_texts(self):
        self.lbl_title.setText(i18n.t("group_model_params", "Model Parameters"))
        for i in range(self.container_layout.count()):
            item = self.container_layout.itemAt(i)
            group_box = item.widget()
            if isinstance(group_box, QGroupBox):
                g_key = group_box.property("i18n_key")
                if g_key: group_box.setTitle(i18n.t(g_key))
                
                for lbl in group_box.findChildren(QLabel):
                    key = lbl.property("i18n_key")
                    if key: lbl.setText(i18n.t(key))
                for cb in group_box.findChildren(QCheckBox):
                    cb.setText(i18n.t("opt_enabled", "Enabled"))
