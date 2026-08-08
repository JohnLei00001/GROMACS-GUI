"""GROMACS-GUI 设计系统（基于 SoftVercel Design Library）

SoftVercel 风格 token：
- 暖调近黑背景 #111110 / 柔和暖白前景 #e9e9e6（非纯白，低对比护眼）
- 青绿品牌色 accent #1f6f64（主操作 / 焦点 / 进度 / 数据）
- 完整暖灰中性色阶 sv-neutral（10 阶）+ 功能色各 10 阶
- 标题 Space Grotesk / 正文 Inter / 等宽 JetBrains Mono
- 圆角 6/8px、输入高度 36px、极浅柔和阴影

控件分类 → 样式（内容分层）：
- 主操作按钮（运行模拟）→ accent 青绿实底
- 次要操作按钮（保存/浏览/测试）→ 卡片底 + 边框
- 幽灵操作（清空/取消）→ 透明 + hover 灰底
- 页面/卡片标题 → Space Grotesk 600 + 暖白 foreground
- 表单标签 / 正文 → Inter 400 + muted-foreground
- 说明 / 弱化信息 → 更暗暖灰（caption 级）
- 分组标签 → eyebrow 风格（11px 600 大写 0.08em 字距）
- 导航项 → muted 文字 + 选中灰底暖白字
- 状态徽章 → 全圆角胶囊 + 功能色
- 编号徽章 → accent 深色底 + 浅青绿字

对外 API：
- build_qss(mode)      生成指定模式的完整 QSS
- apply_theme(app)     应用当前模式：字体 + palette + QSS + matplotlib 适配
- get_mode()/set_mode(mode)  读取 / 切换主题模式
- palette(mode=None)   获取当前主题色板
- set_role(widget, role)     为控件设置角色样式（随主题自动更新）
- status_color(state)  兼容旧 API：返回状态标签的 QSS 颜色串（当前主题）
"""

from PyQt6.QtGui import QFont

# ── 主题 token（SoftVercel Design Library） ───────────────────────────────────
PALETTES = {
    "dark": {
        # 表面（background / card / popover / input）
        "bg":            "#111110",   # background
        "bg_muted":      "#111110",   # 侧边栏与背景同色，靠边框区分
        "bg_panel":      "#161615",   # card
        "bg_input":      "#1a1a19",   # popover（输入框略亮于卡片）
        "bg_hover":      "#262625",   # sv-neutral-900
        "bg_selected":   "#2b2a28",   # sv-primary-800
        "bg_code":       "#0e0e0d",   # 日志代码区（最深）
        # 前景（暖白，低对比护眼）
        "fg":            "#e9e9e6",   # foreground
        "fg_muted":      "#a8a8a3",   # muted-foreground
        "fg_dim":        "#6b6b67",   # sv-neutral-600
        "fg_on_primary": "#f7f7f5",   # on-primary
        # 强调（SoftVercel 青绿品牌色）
        "accent":        "#1f6f64",   # accent-600
        "accent_hover":  "#1a5a52",   # accent-700
        "accent_deep":   "#16463f",   # accent-800（编号徽章底）
        "accent_soft":   "#b2d9d3",   # accent-200（编号徽章字）
        "accent_blue":   "#1f6f64",   # 兼容旧引用（= accent）
        # 主操作（青绿） / 导航选中（暖灰）
        "primary":       "#2b2a28",   # sv-primary-800
        "primary_hover": "#454440",   # sv-primary-700
        "primary_deep":  "#1a1a19",   # sv-primary-900
        "nav_checked_bg": "#262625",  # 导航选中底（暖灰）
        "nav_checked_fg": "#f7f7f5",  # 导航选中字
        # 边框（暖调）
        "border":        "#2b2a28",   # border / rule
        "border_strong": "#3a3a37",   # sv-neutral-800
        # 功能状态色（深色下用浅亮调文字）
        "success":       "#87c091",   # sv-success-300
        "success_text":  "#b4d9b8",   # sv-success-200
        "error":         "#df8788",   # sv-error-300
        "error_text":    "#eeb3b4",   # sv-error-200
        "running":       "#e8c66a",   # sv-warning-300
        "info":          "#85addb",   # sv-info-300
        # 滚动条
        "scroll":        "#3a3a37",
        "scroll_hover":  "#52524f",
        # 文字层级补充
        "input_fg":      "#d4d4d0",
        "btn_bg":        "#1a1a19",   # 默认按钮（popover 底）
        "btn_hover":     "#262625",
        "placeholder":   "#6b6b67",
        "arrow_hex":     "a8a8a3",    # 下拉箭头 SVG 颜色（hex 无 #）
    },
    "light": {
        "bg":            "#fafaf9",   # background
        "bg_muted":      "#fafaf9",
        "bg_panel":      "#fbfbfa",   # card
        "bg_input":      "#ffffff",
        "bg_hover":      "#ececea",   # primary-container
        "bg_selected":   "#e4e4e1",   # surface-container-high
        "bg_code":       "#f2f2f0",   # surface-container-low
        "fg":            "#262625",   # foreground
        "fg_muted":      "#878783",   # muted-foreground
        "fg_dim":        "#a8a8a3",   # sv-neutral-400
        "fg_on_primary": "#f7f7f5",
        "accent":        "#1f6f64",
        "accent_hover":  "#1a5a52",
        "accent_deep":   "#16463f",
        "accent_soft":   "#b2d9d3",
        "accent_blue":   "#1f6f64",
        "primary":       "#2b2a28",
        "primary_hover": "#454440",
        "primary_deep":  "#1a1a19",
        "nav_checked_bg": "#ececea",
        "nav_checked_fg": "#1a1a19",
        "border":        "#e4e4e1",
        "border_strong": "#cfcfcb",
        "success":       "#2c6c42",
        "success_text":  "#255738",
        "error":         "#973235",
        "error_text":    "#7a292b",
        "running":       "#a36e1c",
        "info":          "#30598f",
        "scroll":        "#cfcfcb",
        "scroll_hover":  "#a8a8a3",
        "input_fg":      "#262625",
        "btn_bg":        "#ffffff",
        "btn_hover":     "#f2f2f0",
        "placeholder":   "#a8a8a3",
        "arrow_hex":     "878783",    # 下拉箭头 SVG 颜色（hex 无 #）
    },
}

# matplotlib 配色（SoftVercel chart 色系）
MPL_STYLE = {
    "dark": {
        "figure.facecolor":  "#111110",
        "figure.edgecolor":  "#111110",
        "axes.facecolor":    "#111110",
        "axes.edgecolor":    "#2b2a28",
        "axes.labelcolor":   "#e9e9e6",
        "axes.titlecolor":   "#e9e9e6",
        "text.color":        "#e9e9e6",
        "xtick.color":       "#a8a8a3",
        "ytick.color":       "#a8a8a3",
        "grid.color":        "#262625",
        "grid.alpha":        0.9,
        "lines.linewidth":   1.2,
        "axes.prop_cycle":   ("cycler('color', ['#2f877a', '#3d6fae', '#dca83e',"
                              " '#cc5f60', '#7a7975'])"),
    },
    "light": {
        "figure.facecolor":  "#fafaf9",
        "figure.edgecolor":  "#fafaf9",
        "axes.facecolor":    "#fafaf9",
        "axes.edgecolor":    "#e4e4e1",
        "axes.labelcolor":   "#262625",
        "axes.titlecolor":   "#262625",
        "text.color":        "#262625",
        "xtick.color":       "#878783",
        "ytick.color":       "#878783",
        "grid.color":        "#ececea",
        "grid.alpha":        0.9,
        "lines.linewidth":   1.2,
        "axes.prop_cycle":   ("cycler('color', ['#2f877a', '#3d6fae', '#dca83e',"
                              " '#cc5f60', '#7a7975'])"),
    },
}

# ── 字体（SoftVercel：Grotesk 标题 / Inter 正文 / Mono 等宽） ─────────────────
FONT_HEADING = '"Space Grotesk", "Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif'
FONT_FAMILY = '"Inter", "Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif'
MONO_FAMILY = '"JetBrains Mono", "Cascadia Mono", "Cascadia Code", Consolas, monospace'
APP_FONT_SIZE = 10          # QApplication 默认字号 (pt)
UI_FONT_SIZE = 13           # 正文/表单字号 (px)
SMALL_FONT_SIZE = 11        # caption 字号 (px)
EYEBROW_SIZE = 11           # 分组标签字号 (px)

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
    """为控件设置角色样式（QSS 属性选择器），主题切换时自动跟随。

    仅当角色确实变化时才 unpolish/polish（该操作较重量，避免切换时卡顿）。
    """
    if widget.property("role") == role:
        return
    widget.setProperty("role", role)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def status_color(state: str) -> str:
    """返回状态标签的 QSS 颜色字符串（兼容旧 API，使用当前主题色板）"""
    C = palette()
    _MAP = {
        "idle":     C["fg_muted"],
        "ok":       C["success_text"],
        "running":  C["running"],
        "error":    C["error_text"],
    }
    c = _MAP.get(state, C["fg_muted"])
    return f"color: {c}; font-weight: bold; font-size: 11pt;"


# ── 静态结构 QSS（与主题无关，启动时设置一次，切换不更新） ─────────────────────
_STRUCT_QSS = """
QWidget {
    font-family: "Inter", "Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif;
    font-size: 13px;
}
QLabel { font-size: 13px; }
QMainWindow, QDialog { }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QStackedWidget { border: none; background: transparent; }
QLabel#appTitle {
    font-family: "Space Grotesk", "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 14px; font-weight: 600; letter-spacing: -0.01em;
}
QToolButton#topBtn, QToolButton#winBtn, QToolButton#winClose {
    border: 1px solid transparent; border-radius: 6px; padding: 5px 10px;
}
QToolButton#winClose:hover { color: #ffffff; }
QLabel#navSection {
    font-size: 11px; font-weight: 600; padding: 16px 10px 4px 10px;
    letter-spacing: 0.08em; text-transform: uppercase;
}
QToolButton#navItem {
    border: none; border-radius: 6px; padding: 8px 12px; text-align: left;
}
QFrame#stepCard { border: 1px solid; border-radius: 8px; }
QLabel#stepIndex {
    border: 1px solid; border-radius: 14px; font-weight: 600;
}
QLabel#stepTitle {
    font-family: "Space Grotesk", "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 14px; font-weight: 600; letter-spacing: -0.01em;
}
QLabel#stepSub { font-size: 11px; }
QTabWidget::pane { border: none; top: 0; background-color: transparent; }
QTabBar::tab {
    background: transparent; padding: 8px 14px; border: none;
    border-bottom: 2px solid transparent; margin-right: 2px; font-size: 13px;
}
QPushButton {
    border: 1px solid; border-radius: 6px; padding: 6px 14px; font-size: 13px;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    border: 1px solid; border-radius: 6px; padding: 7px 10px; min-height: 20px;
}
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView { border: 1px solid; border-radius: 6px; padding: 4px; outline: none; }
QCheckBox, QRadioButton { spacing: 6px; }
QCheckBox::indicator, QRadioButton::indicator {
    width: 15px; height: 15px; border: 1px solid; border-radius: 4px;
}
QRadioButton::indicator { border-radius: 8px; }
QTextEdit#logOutput, QTextEdit#rawMdp, QPlainTextEdit {
    border: 1px solid; border-radius: 8px;
    font-family: "JetBrains Mono", "Cascadia Mono", "Cascadia Code", Consolas, monospace;
    font-size: 11px; padding: 6px;
}
QTextEdit { border: 1px solid; border-radius: 8px; }
QProgressBar { border: 1px solid; border-radius: 4px; text-align: center; height: 14px; }
QProgressBar::chunk { border-radius: 3px; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical { border-radius: 4px; min-height: 30px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 8px; margin: 0; }
QScrollBar::handle:horizontal { border-radius: 4px; min-width: 30px; margin: 2px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QStatusBar { border-top: 1px solid; font-size: 11px; }
QStatusBar::item { border: none; }
QMenu { border: 1px solid; border-radius: 8px; padding: 4px; }
QMenu::item { padding: 5px 22px 5px 12px; border-radius: 6px; }
QToolTip { border: 1px solid; border-radius: 6px; padding: 4px 8px; font-size: 11px; }
QListWidget, QListView, QTreeWidget { border: 1px solid; border-radius: 8px; outline: none; }
QListWidget::item { padding: 4px 8px; border-radius: 6px; }
QToolButton[role="section"] {
    border: none; background: transparent; font-weight: 600; padding: 2px 2px;
    text-align: left; font-size: 13px;
}
QLabel[role="section"] { font-weight: 600; margin-top: 10px; margin-bottom: 5px; }
QLabel[role="ok"], QLabel[role="error"], QLabel[role="running"] { font-weight: 600; font-size: 11pt; }
QLabel#tag { border-radius: 9999px; padding: 2px 10px; font-size: 11px; font-weight: 500; }
QLabel[role="muted"] { font-size: 11px; }
QCheckBox { color: palette(text); }
"""


def _build_role_qss(mode: str = None) -> str:
    """生成仅含角色颜色 / 特殊控件的 QSS（随主题切换，规则数少）"""
    import os
    C = palette(mode)
    # 下拉箭头 PNG 路径（QSS image 只支持位图；dark/light 各一）
    arrow_name = "arrow_dark.png" if palette(mode)["bg"] == "#111110" else "arrow_light.png"
    arrow_path = os.path.join(_ensure_arrow_pngs(), arrow_name).replace("\\", "/")
    return f"""
QMainWindow, QDialog {{ background-color: {C["bg"]}; }}
QWidget {{ color: {C["fg"]}; }}
QLabel {{ color: {C["fg_muted"]}; }}
QCheckBox, QRadioButton {{ color: {C["input_fg"]}; }}
QLineEdit::placeholder, QComboBox::placeholder {{ color: {C["placeholder"]}; }}
QWidget#topBar {{ background-color: {C["bg"]}; border-bottom: 1px solid {C["border"]}; }}
QLabel#appTitle {{ color: {C["fg"]}; }}
QToolButton#topBtn {{ background: transparent; color: {C["fg_muted"]}; }}
QToolButton#topBtn:hover {{ color: {C["fg"]}; background-color: {C["bg_hover"]}; border-color: {C["border"]}; }}
QToolButton#topBtn:pressed {{ background-color: {C["bg_selected"]}; }}
QWidget#topBarSep {{ background-color: {C["border"]}; }}
QToolButton#winBtn, QToolButton#winClose {{ background: transparent; color: {C["fg_muted"]}; }}
QToolButton#winBtn:hover {{ background-color: {C["bg_hover"]}; color: {C["fg"]}; }}
QToolButton#winClose:hover {{ background-color: {C["error"]}; }}
QWidget#sidebar {{ background-color: {C["bg_muted"]}; border-right: 1px solid {C["border"]}; }}
QLabel#navSection {{ color: {C["fg_dim"]}; }}
QToolButton#navItem {{ background: transparent; color: {C["fg_muted"]}; }}
QToolButton#navItem:hover {{ background-color: {C["bg_hover"]}; color: {C["fg"]}; }}
QToolButton#navItem:checked {{ background-color: {C["nav_checked_bg"]}; color: {C["nav_checked_fg"]}; font-weight: 600; }}
QFrame#stepCard {{ background-color: {C["bg_panel"]}; border-color: {C["border"]}; }}
QLabel#stepIndex {{ background-color: {C["accent_deep"]}; color: {C["accent_soft"]}; border-color: {C["accent_hover"]}; }}
QLabel#stepTitle {{ color: {C["fg"]}; }}
QLabel#stepSub {{ color: {C["fg_dim"]}; }}
/* 页签栏背景不透明：避免滚动模式下左侧渐变遮罩渲染成黑折线 */
QTabBar {{
    background-color: {C["bg"]};
}}
QTabBar::tab {{
    color: {C["fg_muted"]};
}}
QTabBar::tab:hover {{
    color: {C["fg"]};
}}
QTabBar::tab:selected {{
    color: {C["fg"]};
    border-bottom: 2px solid {C["accent"]};
    font-weight: 600;
}}
QPushButton {{ background-color: {C["btn_bg"]}; color: {C["fg"]}; border-color: {C["border"]}; }}
QPushButton:hover {{ background-color: {C["btn_hover"]}; border-color: {C["fg_muted"]}; }}
QPushButton:pressed {{ background-color: {C["bg_selected"]}; }}
QPushButton:disabled {{ background-color: {C["bg_muted"]}; color: {C["fg_dim"]}; border-color: {C["border"]}; }}
QPushButton[role="primary"] {{ background-color: {C["accent"]}; color: {C["fg_on_primary"]}; border-color: {C["accent"]}; font-weight: 600; }}
QPushButton[role="primary"]:hover {{ background-color: {C["accent_hover"]}; border-color: {C["accent_hover"]}; }}
QPushButton[role="primary"]:pressed {{ background-color: {C["accent_deep"]}; }}
QPushButton[role="primary"]:disabled {{ background-color: {C["bg_muted"]}; color: {C["fg_dim"]}; border-color: {C["border"]}; }}
QPushButton[role="ghost"] {{ background: transparent; border: 1px solid transparent; color: {C["fg_muted"]}; }}
QPushButton[role="ghost"]:hover {{ background-color: {C["bg_hover"]}; color: {C["fg"]}; border-color: {C["border"]}; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background-color: {C["bg_input"]}; border-color: {C["border"]}; color: {C["input_fg"]}; selection-background-color: {C["accent"]}; selection-color: {C["fg_on_primary"]}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {C["accent"]}; }}
QLineEdit:disabled, QComboBox:disabled {{ background-color: {C["bg_muted"]}; color: {C["fg_dim"]}; }}
QComboBox::down-arrow {{ image: url({arrow_path}); width: 10px; height: 6px; margin-right: 8px; }}
QComboBox QAbstractItemView {{ background-color: {C["bg_input"]}; border-color: {C["border_strong"]}; selection-background-color: {C["accent"]}; selection-color: {C["fg_on_primary"]}; }}
QCheckBox::indicator, QRadioButton::indicator {{ border-color: {C["border_strong"]}; background-color: {C["bg_input"]}; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {C["accent"]}; }}
QCheckBox::indicator:checked {{ background-color: {C["accent"]}; border-color: {C["accent"]}; }}
QRadioButton::indicator:checked {{ background-color: {C["accent"]}; border-color: {C["accent"]}; }}
QLabel[role="ok"] {{ color: {C["success_text"]}; }}
QLabel[role="error"] {{ color: {C["error_text"]}; }}
QLabel[role="running"] {{ color: {C["running"]}; }}
QLabel[role="muted"] {{ color: {C["fg_dim"]}; }}
QLabel[role="hint"] {{ color: {C["fg_dim"]}; }}
QLabel[role="hint-italic"] {{ color: {C["fg_dim"]}; font-style: italic; }}
QLabel[role="section"] {{ color: {C["fg"]}; }}
QToolButton[role="section"] {{ color: {C["fg_muted"]}; }}
QToolButton[role="section"]:hover {{ color: {C["fg"]}; }}
QLabel#tag[role="ok"] {{ color: {C["success"]}; background-color: {C["bg_hover"]}; }}
QLabel#tag[role="error"] {{ color: {C["error"]}; background-color: {C["bg_hover"]}; }}
QLabel#tag[role="running"] {{ color: {C["running"]}; background-color: {C["bg_hover"]}; }}
QLabel#tag[role="muted"] {{ color: {C["fg_muted"]}; background-color: {C["bg_hover"]}; }}
QTextEdit#logOutput, QTextEdit#rawMdp, QPlainTextEdit {{ background-color: {C["bg_code"]}; color: {C["input_fg"]}; border-color: {C["border"]}; selection-background-color: {C["accent"]}; selection-color: {C["fg_on_primary"]}; }}
QTextEdit {{ background-color: {C["bg_input"]}; border-color: {C["border"]}; color: {C["input_fg"]}; selection-background-color: {C["accent"]}; selection-color: {C["fg_on_primary"]}; }}
QProgressBar {{ background-color: {C["bg_input"]}; border: 1px solid {C["border"]}; color: {C["fg"]}; }}
QProgressBar::chunk {{ background-color: {C["accent"]}; }}
QScrollBar::handle:vertical {{ background: {C["scroll"]}; }}
QScrollBar::handle:vertical:hover {{ background: {C["scroll_hover"]}; }}
QScrollBar::handle:horizontal {{ background: {C["scroll"]}; }}
QScrollBar::handle:horizontal:hover {{ background: {C["scroll_hover"]}; }}
QStatusBar {{ background-color: {C["bg"]}; color: {C["fg_muted"]}; border-top-color: {C["border"]}; }}
QMenu {{ background-color: {C["bg_input"]}; border-color: {C["border_strong"]}; }}
QMenu::item:selected {{ background-color: {C["accent"]}; color: {C["fg_on_primary"]}; }}
QToolTip {{ background-color: {C["bg_input"]}; color: {C["fg"]}; border-color: {C["border_strong"]}; }}
QListWidget, QListView, QTreeWidget {{ background-color: {C["bg_input"]}; border-color: {C["border"]}; }}
QListWidget::item:hover {{ background-color: {C["bg_hover"]}; }}
QListWidget::item:selected {{ background-color: {C["accent"]}; color: {C["fg_on_primary"]}; }}
"""


def build_qss(mode: str = None) -> str:
    """生成完整 QSS（结构 + 角色颜色），供启动时一次性应用"""
    return _STRUCT_QSS + _build_role_qss(mode)


def get_qss() -> str:
    """返回当前主题的完整 QSS（供弹窗等非主窗口子树应用）"""
    return _STRUCT_QSS + _build_role_qss(CURRENT_MODE)


def _ensure_arrow_pngs() -> str:
    """生成下拉箭头 PNG（QSS image 只支持位图，不支持 SVG），返回资源目录。

    箭头为 10x6 圆角 V 形，颜色随主题（dark: #a8a8a3 / light: #878783）。
    纯 Python 生成，无 QApplication 依赖。
    """
    from gui.arrow_assets import ensure_arrow_pngs
    return ensure_arrow_pngs()


def apply_theme(app, delay_mpl: bool = True) -> None:
    """应用当前模式的设计系统：默认字体 + palette + QSS + matplotlib 适配。

    性能优化：
    - QSS 拆分为「静态结构」+「角色颜色」，设置在顶层主窗口上而非 app 上
      （窗口级 setStyleSheet 只 polish 该窗口树，实测 ~70ms，比应用级快 10 倍）
    - 调色板全局设置（~2ms），保证弹窗/菜单等原生控件随主题
    - matplotlib 延迟到事件循环空闲时刷新，不阻塞切换

    delay_mpl=True 时 matplotlib 配色延迟到空闲时再刷新。
    """
    from PyQt6.QtGui import QColor, QPalette

    # 1. 默认字体（Inter 优先，回退 Segoe UI / 微软雅黑）
    f = QFont("Segoe UI", APP_FONT_SIZE)
    f.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(f)

    # 2. 应用级调色板：无边框窗口首帧即为主题背景 + 弹窗/菜单跟随主题
    C = palette(CURRENT_MODE)
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(C["bg"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(C["fg"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(C["bg_input"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(C["bg_muted"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(C["fg"]))
    pal.setColor(QPalette.ColorRole.Button, QColor(C["btn_bg"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(C["fg"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(C["bg_input"]))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(C["fg"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(C["accent"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(C["fg_on_primary"]))
    app.setPalette(pal)

    # 3. 全局样式表（随当前模式），设置在顶层窗口上（若已创建）
    qss = _STRUCT_QSS + _build_role_qss(CURRENT_MODE)
    top_widgets = [w for w in app.topLevelWidgets() if w.isVisible()]
    if top_widgets:
        # 窗口级：只 polish 该窗口树（~70ms，避免应用级全量 polish ~800ms）
        for w in top_widgets:
            w.setStyleSheet(qss)
    else:
        app.setStyleSheet(qss)

    # 4. matplotlib 配色适配（若已安装）：延迟到空闲时执行，不阻塞切换
    if delay_mpl:
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: _apply_matplotlib(CURRENT_MODE))
    else:
        _apply_matplotlib(CURRENT_MODE)


def _apply_matplotlib(mode: str) -> None:
    """将 matplotlib 默认样式切换为与当前主题一致的配色"""
    try:
        import matplotlib
        matplotlib.rcParams.update(MPL_STYLE[mode])
    except ImportError:
        pass
