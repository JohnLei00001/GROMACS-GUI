"""GROMACS-GUI 设计系统（基于「极简」设计库）

结构重构后的设计规范：
- token 体系：单色中性色阶（黑/白/灰）+ 功能状态色，亮/暗双主题同构
- 组件体系：应用栏 / 侧边导航 / 步骤卡片 / 三级按钮 / 状态徽章 / 页签 / 输入 / 日志
- 排版：13px 正文、11px 辅助、15px 卡片标题；8-12px 圆角；4px 间距基准

对外 API：
- build_qss(mode)      生成指定模式的完整 QSS
- apply_theme(app)     应用当前模式：字体 + QSS + matplotlib 适配
- get_mode()/set_mode(mode)  读取 / 切换主题模式
- palette(mode=None)   获取当前主题色板
- set_role(widget, role)     为控件设置角色样式（随主题自动更新）
- status_color(state)  兼容旧 API：返回状态标签的 QSS 颜色串（当前主题）
"""

from PyQt6.QtGui import QFont

# ── 主题 token（映射「极简」设计库语义角色） ───────────────────────────────────
PALETTES = {
    "light": {
        # 表面（background / card / muted / input / elevated）
        "bg":            "#ffffff",   # background-50
        "bg_muted":      "#fafafa",   # background-100 / muted / sidebar
        "bg_panel":      "#ffffff",   # card
        "bg_input":      "#ffffff",   # input
        "bg_hover":      "#f4f4f5",   # brand-100
        "bg_selected":   "#f4f4f5",   # accent
        "bg_code":       "#fafafa",   # code surface
        # 前景
        "fg":            "#18181b",   # foreground (brand-900)
        "fg_muted":      "#71717a",   # muted-foreground (brand-500)
        "fg_dim":        "#a1a1aa",   # brand-400
        "fg_on_primary": "#fafafa",   # primary-foreground (brand-50)
        # 强调（极简：近黑主色）
        "primary":       "#18181b",
        "primary_hover": "#3f3f46",
        # 边框
        "border":        "#e4e4e7",   # border (brand-200)
        "border_strong": "#d4d4d8",   # border-strong (brand-300)
        # 功能状态色
        "success":       "#16a34a",
        "success_text":  "#15803d",
        "error":         "#dc2626",
        "error_text":    "#b91c1c",
        "running":       "#d97706",
        # 滚动条 / 分割
        "scroll":        "#d4d4d8",
        "scroll_hover":  "#a1a1aa",
    },
    "dark": {
        "bg":            "#18181b",   # brand-900
        "bg_muted":      "#27272a",   # brand-800 / muted / sidebar
        "bg_panel":      "#27272a",   # card (brand-800)
        "bg_input":      "#27272a",   # input
        "bg_hover":      "#3f3f46",   # brand-700
        "bg_selected":   "#3f3f46",   # accent
        "bg_code":       "#0a0a0a",   # background-900
        "fg":            "#fafafa",   # brand-50
        "fg_muted":      "#a1a1aa",   # brand-400
        "fg_dim":        "#71717a",   # brand-500
        "fg_on_primary": "#18181b",
        "primary":       "#fafafa",
        "primary_hover": "#e4e4e7",
        "border":        "#3f3f46",
        "border_strong": "#52525b",
        "success":       "#22c55e",
        "success_text":  "#4ade80",
        "error":         "#ef4444",
        "error_text":    "#fca5a5",
        "running":       "#fbbf24",
        "scroll":        "#52525b",
        "scroll_hover":  "#71717a",
    },
}

# matplotlib 配色（亮 / 暗）
MPL_STYLE = {
    "light": {
        "figure.facecolor":  "#ffffff",
        "figure.edgecolor":  "#ffffff",
        "axes.facecolor":    "#ffffff",
        "axes.edgecolor":    "#d4d4d8",
        "axes.labelcolor":   "#18181b",
        "axes.titlecolor":   "#18181b",
        "text.color":        "#18181b",
        "xtick.color":       "#71717a",
        "ytick.color":       "#71717a",
        "grid.color":        "#e4e4e7",
        "grid.alpha":        0.8,
        "lines.linewidth":   1.2,
    },
    "dark": {
        "figure.facecolor":  "#18181b",
        "figure.edgecolor":  "#18181b",
        "axes.facecolor":    "#18181b",
        "axes.edgecolor":    "#3f3f46",
        "axes.labelcolor":   "#fafafa",
        "axes.titlecolor":   "#fafafa",
        "text.color":        "#fafafa",
        "xtick.color":       "#a1a1aa",
        "ytick.color":       "#a1a1aa",
        "grid.color":        "#3f3f46",
        "grid.alpha":        0.8,
        "lines.linewidth":   1.2,
    },
}

# ── 字体 ─────────────────────────────────────────────────────────────────────
FONT_FAMILY = '"Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif'
MONO_FAMILY = '"Cascadia Mono", "Cascadia Code", Consolas, "Courier New", monospace'
APP_FONT_SIZE = 10          # QApplication 默认字号 (pt)
UI_FONT_SIZE = 13           # 界面字号 (px)
SMALL_FONT_SIZE = 11        # 次要字号 (px)

# ── 主题模式（默认深色，main 启动时按配置覆盖） ────────────────────────────────
CURRENT_MODE = "dark"


def get_mode() -> str:
    return CURRENT_MODE


def set_mode(mode: str) -> None:
    global CURRENT_MODE
    if mode in PALETTES:
        CURRENT_MODE = mode


def palette(mode: str = None) -> dict:
    return PALETTES[mode if mode in PALETTES else CURRENT_MODE]


# ── 状态角色映射（供各 Tab 状态标签使用，随主题自动切换） ──────────────────────
def set_role(widget, role: str) -> None:
    """为控件设置角色样式（QSS 属性选择器），主题切换时自动跟随"""
    widget.setProperty("role", role)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def status_color(state: str) -> str:
    """返回状态标签的 QSS 颜色字符串（兼容旧 API，使用当前主题色板）。

    用法: label.setStyleSheet(status_color("ok"))
    """
    C = palette()
    _MAP = {
        "idle":     C["fg_muted"],
        "ok":       C["success_text"],
        "running":  C["running"],
        "error":    C["error_text"],
    }
    c = _MAP.get(state, C["fg_muted"])
    return f"color: {c}; font-weight: bold; font-size: 11pt;"


def build_qss(mode: str = None) -> str:
    """生成指定主题模式的完整 QSS 样式表"""
    C = palette(mode)
    return f"""
/* ═══ 基础 ═══ */
QMainWindow, QDialog {{
    background-color: {C["bg"]};
}}
QWidget {{
    color: {C["fg"]};
    font-family: {FONT_FAMILY};
    font-size: {UI_FONT_SIZE}px;
}}

/* ═══ 无边框容器（滚动区 / 堆叠区，消除多余黑框） ═══ */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QStackedWidget {{
    border: none;
    background: transparent;
}}

/* ═══ 顶部应用栏（#topBar） ═══ */
QWidget#topBar {{
    background-color: {C["bg"]};
    border-bottom: 1px solid {C["border"]};
}}
QLabel#appTitle {{
    color: {C["fg"]};
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.3px;
}}
QToolButton#topBtn {{
    background: transparent;
    color: {C["fg_muted"]};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 5px 12px;
    font-size: {UI_FONT_SIZE}px;
}}
QToolButton#topBtn:hover {{
    color: {C["fg"]};
    background-color: {C["bg_hover"]};
    border-color: {C["border"]};
}}
QToolButton#topBtn:pressed {{
    background-color: {C["bg_selected"]};
}}
/* 自绘标题栏窗口控制 */
QWidget#topBarSep {{
    background-color: {C["border"]};
}}
QToolButton#winBtn, QToolButton#winClose {{
    background: transparent;
    color: {C["fg_muted"]};
    border: none;
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 13px;
}}
QToolButton#winBtn:hover {{
    background-color: {C["bg_hover"]};
    color: {C["fg"]};
}}
QToolButton#winClose:hover {{
    background-color: {C["error"]};
    color: #ffffff;
}}

/* ═══ 侧边导航（#sidebar） ═══ */
QWidget#sidebar {{
    background-color: {C["bg_muted"]};
    border-right: 1px solid {C["border"]};
}}
QLabel#navSection {{
    color: {C["fg_dim"]};
    font-size: 11px;
    font-weight: 600;
    padding: 14px 10px 4px 10px;
    letter-spacing: 0.5px;
}}
QToolButton#navItem {{
    background: transparent;
    color: {C["fg_muted"]};
    border: none;
    border-radius: 8px;
    padding: 9px 12px;
    font-size: {UI_FONT_SIZE}px;
    text-align: left;
}}
QToolButton#navItem:hover {{
    background-color: {C["bg_hover"]};
    color: {C["fg"]};
}}
QToolButton#navItem:checked {{
    background-color: {C["primary"]};
    color: {C["fg_on_primary"]};
    font-weight: 600;
}}
/* 导航状态点（子控件占位符：序号后的圆点由属性驱动） */

/* ═══ 步骤卡片（#stepCard） ═══ */
QFrame#stepCard {{
    background-color: {C["bg_panel"]};
    border: 1px solid {C["border"]};
    border-radius: 12px;
}}
QLabel#stepIndex {{
    background-color: {C["bg_hover"]};
    color: {C["fg"]};
    border: 1px solid {C["border"]};
    border-radius: 14px;
    font-weight: bold;
}}
QLabel#stepTitle {{
    color: {C["fg"]};
    font-size: 15px;
    font-weight: 600;
}}
QLabel#stepSub {{
    color: {C["fg_muted"]};
    font-size: {SMALL_FONT_SIZE}px;
}}

/* ═══ 页签 ═══ */
QTabWidget::pane {{
    border: none;
    top: 0;
    background-color: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {C["fg_muted"]};
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
    font-size: {UI_FONT_SIZE}px;
}}
QTabBar::tab:hover {{
    color: {C["fg"]};
}}
QTabBar::tab:selected {{
    color: {C["fg"]};
    border-bottom: 2px solid {C["primary"]};
    font-weight: 600;
}}

/* ═══ 按钮（三级：默认 / primary / ghost） ═══ */
QPushButton {{
    background-color: {C["bg_panel"]};
    color: {C["fg"]};
    border: 1px solid {C["border_strong"]};
    border-radius: 8px;
    padding: 6px 16px;
    font-size: {UI_FONT_SIZE}px;
}}
QPushButton:hover {{
    background-color: {C["bg_hover"]};
    border-color: {C["fg_muted"]};
}}
QPushButton:pressed {{
    background-color: {C["bg_selected"]};
}}
QPushButton:disabled {{
    background-color: {C["bg_muted"]};
    color: {C["fg_dim"]};
    border-color: {C["border"]};
}}
QPushButton[role="primary"] {{
    background-color: {C["primary"]};
    color: {C["fg_on_primary"]};
    border: 1px solid {C["primary"]};
    font-weight: 600;
}}
QPushButton[role="primary"]:hover {{
    background-color: {C["primary_hover"]};
    border-color: {C["primary_hover"]};
}}
QPushButton[role="primary"]:pressed {{
    background-color: {C["fg_muted"]};
}}
QPushButton[role="primary"]:disabled {{
    background-color: {C["bg_muted"]};
    color: {C["fg_dim"]};
    border-color: {C["border"]};
}}
QPushButton[role="ghost"] {{
    background: transparent;
    border: 1px solid transparent;
    color: {C["fg_muted"]};
}}
QPushButton[role="ghost"]:hover {{
    background-color: {C["bg_hover"]};
    color: {C["fg"]};
    border-color: {C["border"]};
}}

/* ═══ 输入控件 ═══ */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {C["bg_input"]};
    border: 1px solid {C["border_strong"]};
    border-radius: 8px;
    padding: 5px 9px;
    color: {C["fg"]};
    selection-background-color: {C["primary"]};
    selection-color: {C["fg_on_primary"]};
    min-height: 16px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {C["primary"]};
}}
QLineEdit:disabled, QComboBox:disabled {{
    background-color: {C["bg_muted"]};
    color: {C["fg_dim"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 26px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {C["fg_muted"]};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {C["bg_panel"]};
    border: 1px solid {C["border_strong"]};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {C["primary"]};
    selection-color: {C["fg_on_primary"]};
    outline: none;
}}

/* ═══ 复选框 / 单选钮 ═══ */
QCheckBox, QRadioButton {{
    spacing: 6px;
    color: {C["fg"]};
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {C["border_strong"]};
    border-radius: 4px;
    background-color: {C["bg_input"]};
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {C["primary"]};
}}
QCheckBox::indicator:checked {{
    background-color: {C["primary"]};
    border-color: {C["primary"]};
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
QRadioButton::indicator:checked {{
    background-color: {C["primary"]};
    border-color: {C["primary"]};
}}

/* ═══ 状态角色（QLabel / QToolButton 通用） ═══ */
QLabel[role="ok"] {{
    color: {C["success_text"]};
    font-weight: bold;
    font-size: 11pt;
}}
QLabel[role="error"] {{
    color: {C["error_text"]};
    font-weight: bold;
    font-size: 11pt;
}}
QLabel[role="running"] {{
    color: {C["running"]};
    font-weight: bold;
    font-size: 11pt;
}}
QLabel[role="muted"] {{
    color: {C["fg_muted"]};
    font-size: {SMALL_FONT_SIZE}px;
}}
QLabel[role="hint"] {{
    color: {C["fg_muted"]};
    font-size: {UI_FONT_SIZE}px;
}}
QLabel[role="hint-italic"] {{
    color: {C["fg_muted"]};
    font-size: {UI_FONT_SIZE}px;
    font-style: italic;
}}
QLabel[role="section"] {{
    color: {C["fg"]};
    font-weight: bold;
    margin-top: 10px;
    margin-bottom: 5px;
}}
QToolButton[role="section"] {{
    border: none;
    background: transparent;
    color: {C["fg_muted"]};
    font-weight: bold;
    padding: 2px 2px;
    text-align: left;
    font-size: {UI_FONT_SIZE}px;
}}
QToolButton[role="section"]:hover {{
    color: {C["fg"]};
}}

/* ═══ 状态徽章（#tag） ═══ */
QLabel#tag {{
    border-radius: 10px;
    padding: 2px 10px;
    font-size: {SMALL_FONT_SIZE}px;
    font-weight: 600;
}}
QLabel#tag[role="ok"] {{
    color: {C["success_text"]};
    background-color: {C["bg_hover"]};
}}
QLabel#tag[role="error"] {{
    color: {C["error_text"]};
    background-color: {C["bg_hover"]};
}}
QLabel#tag[role="running"] {{
    color: {C["running"]};
    background-color: {C["bg_hover"]};
}}
QLabel#tag[role="muted"] {{
    color: {C["fg_muted"]};
    background-color: {C["bg_hover"]};
}}

/* ═══ 日志区（#logOutput / #rawMdp） ═══ */
QTextEdit#logOutput, QTextEdit#rawMdp, QPlainTextEdit {{
    background-color: {C["bg_code"]};
    color: {C["fg"]};
    border: 1px solid {C["border"]};
    border-radius: 8px;
    font-family: {MONO_FAMILY};
    font-size: 11px;
    padding: 6px;
    selection-background-color: {C["primary"]};
    selection-color: {C["fg_on_primary"]};
}}
QTextEdit {{
    background-color: {C["bg_input"]};
    border: 1px solid {C["border"]};
    border-radius: 8px;
    color: {C["fg"]};
    selection-background-color: {C["primary"]};
    selection-color: {C["fg_on_primary"]};
}}

/* ═══ 进度条 ═══ */
QProgressBar {{
    background-color: {C["bg_input"]};
    border: 1px solid {C["border"]};
    border-radius: 5px;
    text-align: center;
    color: {C["fg"]};
    height: 14px;
}}
QProgressBar::chunk {{
    background-color: {C["primary"]};
    border-radius: 4px;
}}

/* ═══ 滚动条（现代细条） ═══ */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C["scroll"]};
    border-radius: 4px;
    min-height: 30px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: {C["scroll_hover"]};
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {C["scroll"]};
    border-radius: 4px;
    min-width: 30px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {C["scroll_hover"]};
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
    background-color: {C["bg_muted"]};
    color: {C["fg_muted"]};
    border-top: 1px solid {C["border"]};
    font-size: {SMALL_FONT_SIZE}px;
}}
QStatusBar::item {{
    border: none;
}}

/* ═══ 菜单与工具提示 ═══ */
QMenu {{
    background-color: {C["bg_panel"]};
    border: 1px solid {C["border_strong"]};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 5px 22px 5px 12px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background-color: {C["primary"]};
    color: {C["fg_on_primary"]};
}}
QToolTip {{
    background-color: {C["bg_panel"]};
    color: {C["fg"]};
    border: 1px solid {C["border_strong"]};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: {SMALL_FONT_SIZE}px;
}}

/* ═══ 列表 ═══ */
QListWidget, QListView, QTreeWidget {{
    background-color: {C["bg_input"]};
    border: 1px solid {C["border"]};
    border-radius: 8px;
    outline: none;
}}
QListWidget::item {{
    padding: 4px 8px;
    border-radius: 6px;
}}
QListWidget::item:hover {{
    background-color: {C["bg_hover"]};
}}
QListWidget::item:selected {{
    background-color: {C["primary"]};
    color: {C["fg_on_primary"]};
}}
"""


def apply_theme(app) -> None:
    """应用当前模式的设计系统：默认字体 + QSS + matplotlib 适配"""
    from PyQt6.QtGui import QColor, QPalette

    # 1. 默认字体（中英文混排走 Segoe UI + 系统 fallback）
    f = QFont("Segoe UI", APP_FONT_SIZE)
    f.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(f)

    # 2. 应用级调色板：确保无边框窗口首帧即为主题背景，避免启动白闪
    C = palette(CURRENT_MODE)
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(C["bg"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(C["fg"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(C["bg_input"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(C["bg_muted"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(C["fg"]))
    pal.setColor(QPalette.ColorRole.Button, QColor(C["bg_panel"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(C["fg"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(C["bg_panel"]))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(C["fg"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(C["primary"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(C["fg_on_primary"]))
    app.setPalette(pal)

    # 3. 全局样式表（随当前模式）
    app.setStyleSheet(build_qss(CURRENT_MODE))

    # 4. matplotlib 配色适配（若已安装）
    _apply_matplotlib(CURRENT_MODE)


def _apply_matplotlib(mode: str) -> None:
    """将 matplotlib 默认样式切换为与当前主题一致的配色"""
    try:
        import matplotlib
        matplotlib.rcParams.update(MPL_STYLE[mode])
    except ImportError:
        pass
