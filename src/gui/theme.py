"""GROMACS-GUI 设计系统（Design System）

集中管理颜色、字体、间距与全局样式表，提供统一的应用入口：
- build_qss()        生成完整 QSS 样式表
- apply_theme(app)   应用字体 + QSS + matplotlib 深色适配
- status_color(s)    状态标签配色（idle / ok / running / error）

设计原则：
- 深色主题，降低长时间盯屏疲劳，突出数据可视化
- 统一色板（VS Code 系科技蓝强调色），取代散落各处的硬编码颜色
- 8px 圆角、细边框、现代细滚动条，形成一致的视觉语言
"""

# ── 色板 ────────────────────────────────────────────────────────────────────
COLORS = {
    # 背景层级
    "bg_base":        "#1e1e1e",   # 窗口 / 页面
    "bg_panel":       "#252526",   # 分组框 / 面板
    "bg_input":       "#2d2d30",   # 输入框 / 导航项
    "bg_hover":       "#333337",   # 悬停
    "bg_selected":    "#37373d",   # 选中
    "bg_code":        "#1b1b1b",   # 代码 / 日志区
    # 强调色
    "accent":         "#007acc",   # 主强调（VS Code 蓝）
    "accent_hover":   "#0e639c",   # 强调悬停
    # 文本
    "text_main":      "#cccccc",
    "text_sub":       "#8a8a8a",   # 次级文本
    "text_dim":       "#6a6a6a",   # 弱化文本
    "text_bright":    "#ffffff",
    # 边框
    "border":         "#3f3f3f",
    "border_light":   "#4d4d4d",
    # 状态色
    "success":        "#89d185",   # 成功（绿）
    "warning":        "#cca700",   # 警告（黄）
    "error":          "#f48771",   # 错误（红）
    "running":        "#d7ba7d",   # 运行中（琥珀）
}

# ── 字体 ─────────────────────────────────────────────────────────────────────
FONT_FAMILY = '"Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif'
MONO_FAMILY = '"Cascadia Mono", "Cascadia Code", Consolas, "Courier New", monospace'
APP_FONT_SIZE = 10          # QApplication 默认字号 (pt)
UI_FONT_SIZE = 13           # 界面字号 (px)
SMALL_FONT_SIZE = 11        # 次要字号 (px)

# ── 状态色映射（供各 Tab 的状态标签快速统一） ─────────────────────────────────
_STATUS_MAP = {
    "idle":     COLORS["text_sub"],
    "ok":       COLORS["success"],
    "running":  COLORS["running"],
    "error":    COLORS["error"],
}


def status_color(state: str) -> str:
    """返回状态标签的 QSS 颜色字符串。

    用法: label.setStyleSheet(status_color("ok"))
    """
    c = _STATUS_MAP.get(state, COLORS["text_sub"])
    return f"color: {c}; font-weight: bold; font-size: 11pt;"


def build_qss() -> str:
    """生成全局 QSS 样式表"""
    C = COLORS
    return f"""
/* ═══ 基础 ═══ */
QMainWindow, QDialog {{
    background-color: {C["bg_base"]};
}}
QWidget {{
    color: {C["text_main"]};
    font-family: {FONT_FAMILY};
    font-size: {UI_FONT_SIZE}px;
}}

/* ═══ 导航栏（#navList） ═══ */
QListWidget#navList {{
    background-color: {C["bg_panel"]};
    border: none;
    border-right: 1px solid {C["border"]};
    padding: 10px 0;
    color: {C["text_main"]};
    outline: none;
}}
QListWidget#navList::item {{
    padding: 8px 12px;
    margin: 1px 6px;
    border-radius: 6px;
    border-left: 3px solid transparent;
}}
QListWidget#navList::item:hover {{
    background-color: {C["bg_hover"]};
}}
QListWidget#navList::item:selected {{
    background-color: {C["bg_selected"]};
    color: {C["text_bright"]};
    border-left: 3px solid {C["accent"]};
}}

/* ═══ 分组框 ═══ */
QGroupBox {{
    background-color: {C["bg_panel"]};
    border: 1px solid {C["border"]};
    border-radius: 8px;
    margin-top: 10px;
    padding: 5px 8px 7px 8px;
    font-weight: 600;
    color: {C["text_main"]};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: {C["text_sub"]};
    font-size: {SMALL_FONT_SIZE}px;
}}

/* ═══ 标签页 ═══ */
QTabWidget::pane {{
    border: 1px solid {C["border"]};
    border-radius: 6px;
    top: -1px;
    background-color: {C["bg_base"]};
}}
QTabBar::tab {{
    background: transparent;
    color: {C["text_sub"]};
    padding: 5px 12px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
    font-size: {UI_FONT_SIZE}px;
}}
QTabBar::tab:hover {{
    color: {C["text_main"]};
}}
QTabBar::tab:selected {{
    color: {C["text_bright"]};
    border-bottom: 2px solid {C["accent"]};
}}

/* ═══ 按钮 ═══ */
QPushButton {{
    background-color: {C["bg_hover"]};
    color: {C["text_main"]};
    border: 1px solid {C["border_light"]};
    border-radius: 6px;
    padding: 4px 12px;
    font-size: {UI_FONT_SIZE}px;
}}
QPushButton:hover {{
    background-color: {C["bg_selected"]};
    border-color: {C["accent"]};
    color: {C["text_bright"]};
}}
QPushButton:pressed {{
    background-color: {C["bg_input"]};
}}
QPushButton:disabled {{
    background-color: {C["bg_panel"]};
    color: {C["text_dim"]};
    border-color: {C["border"]};
}}

/* ═══ 输入控件 ═══ */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {C["bg_input"]};
    border: 1px solid {C["border"]};
    border-radius: 6px;
    padding: 3px 6px;
    color: {C["text_main"]};
    selection-background-color: {C["accent"]};
    selection-color: {C["text_bright"]};
    min-height: 16px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {C["accent"]};
}}
QLineEdit:disabled, QComboBox:disabled {{
    background-color: {C["bg_panel"]};
    color: {C["text_dim"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {C["text_sub"]};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {C["bg_panel"]};
    border: 1px solid {C["border_light"]};
    selection-background-color: {C["accent"]};
    selection-color: {C["text_bright"]};
    outline: none;
}}

/* ═══ 复选框 / 单选钮 ═══ */
QCheckBox, QRadioButton {{
    spacing: 6px;
    color: {C["text_main"]};
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {C["border_light"]};
    border-radius: 4px;
    background-color: {C["bg_input"]};
}}
QCheckBox::indicator:checked {{
    background-color: {C["accent"]};
    border-color: {C["accent"]};
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
QRadioButton::indicator:checked {{
    background-color: {C["accent"]};
    border-color: {C["accent"]};
}}

/* ═══ 日志区（#logOutput） ═══ */
QTextEdit#logOutput, QTextEdit#rawMdp, QPlainTextEdit {{
    background-color: {C["bg_code"]};
    color: #a8b2c1;
    border: 1px solid {C["border"]};
    border-radius: 6px;
    font-family: {MONO_FAMILY};
    font-size: 11px;
    padding: 6px;
    selection-background-color: {C["accent"]};
    selection-color: {C["text_bright"]};
}}

/* ═══ 进度条 ═══ */
QProgressBar {{
    background-color: {C["bg_input"]};
    border: 1px solid {C["border"]};
    border-radius: 5px;
    text-align: center;
    color: {C["text_bright"]};
    height: 14px;
}}
QProgressBar::chunk {{
    background-color: {C["accent"]};
    border-radius: 4px;
}}

/* ═══ 滚动条（现代细条） ═══ */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #4a4a4f;
    border-radius: 4px;
    min-height: 30px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: #5a5a60;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: #4a4a4f;
    border-radius: 4px;
    min-width: 30px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #5a5a60;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
    width: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

/* ═══ 分割器 ═══ */
QSplitter::handle {{
    background-color: {C["border"]};
}}
QSplitter::handle:vertical {{
    height: 1px;
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}

/* ═══ 状态栏 ═══ */
QStatusBar {{
    background-color: {C["bg_panel"]};
    color: {C["text_sub"]};
    border-top: 1px solid {C["border"]};
    font-size: {SMALL_FONT_SIZE}px;
}}
QStatusBar::item {{
    border: none;
}}

/* ═══ 菜单与工具提示 ═══ */
QMenu {{
    background-color: {C["bg_panel"]};
    border: 1px solid {C["border_light"]};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 4px 20px 4px 10px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {C["accent"]};
    color: {C["text_bright"]};
}}
QToolTip {{
    background-color: {C["bg_selected"]};
    color: {C["text_main"]};
    border: 1px solid {C["border_light"]};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: {SMALL_FONT_SIZE}px;
}}

/* ═══ 列表与文本区（通用） ═══ */
QListWidget, QListView, QTreeWidget {{
    background-color: {C["bg_input"]};
    border: 1px solid {C["border"]};
    border-radius: 6px;
    outline: none;
}}
QListWidget::item {{
    padding: 4px 6px;
    border-radius: 4px;
}}
QListWidget::item:selected {{
    background-color: {C["accent"]};
    color: {C["text_bright"]};
}}
QTextEdit, QPlainTextEdit {{
    background-color: {C["bg_input"]};
    border: 1px solid {C["border"]};
    border-radius: 6px;
    color: {C["text_main"]};
    selection-background-color: {C["accent"]};
    selection-color: {C["text_bright"]};
}}
"""


def apply_theme(app) -> None:
    """应用设计系统到 QApplication：默认字体 + QSS + matplotlib 深色适配"""
    # 1. 默认字体（中英文混排走 Segoe UI + 系统 fallback）
    from PyQt6.QtGui import QFont
    f = QFont("Segoe UI", APP_FONT_SIZE)
    f.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(f)

    # 2. 全局样式表
    app.setStyleSheet(build_qss())

    # 3. matplotlib 深色适配（若已安装）
    _apply_matplotlib_dark()


def _apply_matplotlib_dark() -> None:
    """将 matplotlib 默认样式切换为深色，与 GUI 主题一致"""
    try:
        import matplotlib
        rc = {
            "figure.facecolor":  COLORS["bg_base"],
            "figure.edgecolor":  COLORS["bg_base"],
            "axes.facecolor":    COLORS["bg_panel"],
            "axes.edgecolor":    COLORS["border"],
            "axes.labelcolor":   COLORS["text_main"],
            "axes.titlecolor":   COLORS["text_main"],
            "text.color":        COLORS["text_main"],
            "xtick.color":       COLORS["text_sub"],
            "ytick.color":       COLORS["text_sub"],
            "grid.color":        COLORS["border_light"],
            "grid.alpha":        0.35,
            "lines.linewidth":   1.2,
        }
        matplotlib.rcParams.update(rc)
    except ImportError:
        pass
