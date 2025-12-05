import json
import os
import sys
from PyQt6.QtCore import QObject, pyqtSignal, QLocale

class I18nManager(QObject):
    language_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.translations = {}
        
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        self.lang_dir = os.path.join(base_dir, "app", "lang")
            
        self.current_lang = "en_US"
        self.available_langs = self._scan_languages()

    def _scan_languages(self):
        """扫描 lang 目录下的 json 文件"""
        langs = {}
        if not os.path.exists(self.lang_dir):
            print(f"Error: Lang dir not found: {self.lang_dir}")
            return langs

        for f in os.listdir(self.lang_dir):
            if f.endswith(".json"):
                lang_code = f[:-5]
                langs[lang_code] = f
        return langs

    def auto_init(self):
        """自动检测系统语言并加载"""
        sys_lang = QLocale.system().name()
        if sys_lang in self.available_langs:
            self.load_language(sys_lang)
        elif sys_lang.split('_')[0] in [l.split('_')[0] for l in self.available_langs]:
             for code in self.available_langs:
                 if code.startswith(sys_lang.split('_')[0]):
                     self.load_language(code)
                     return
        else:
            self.load_language("en_US")

    def load_language(self, lang_code):
        if lang_code not in self.available_langs:
            print(f"Warning: Language {lang_code} not found, fallback to en_US")
            lang_code = "en_US"
            if lang_code not in self.available_langs: return

        file_path = os.path.join(self.lang_dir, self.available_langs[lang_code])
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self.current_lang = lang_code
            print(f"Loaded language: {lang_code}")
            self.language_changed.emit()
        except Exception as e:
            print(f"Failed to load language: {e}")

    def t(self, key, default=None):
        """获取翻译文本"""
        return self.translations.get(key, default if default is not None else key)

i18n = I18nManager()