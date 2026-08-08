import sys
import os

# 确保能找到 src 下的模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow
from gui.theme import apply_theme

def main():
    app = QApplication(sys.argv)

    # 基础风格：Fusion 保证跨平台一致
    app.setStyle("Fusion")
    # 设计系统：默认字体 + 深色主题 + matplotlib 深色适配
    apply_theme(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
