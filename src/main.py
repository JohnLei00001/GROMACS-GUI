import sys
import os

# 确保能找到 src 下的模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow
from gui.theme import apply_theme, set_mode
from gui.i18n import set_language
from core.config import get_setting

def main():
    app = QApplication(sys.argv)

    # 基础风格：Fusion 保证跨平台一致
    app.setStyle("Fusion")

    # 读取持久化设置：主题（亮/暗）+ 界面语言（中/英）
    saved_theme = get_setting("theme", "dark")
    saved_lang = get_setting("language", "zh")
    set_mode(saved_theme)
    set_language(saved_lang)

    # 设计系统：默认字体 + 双主题 QSS + matplotlib 适配
    apply_theme(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
