"""GROMACS-GUI 核心 UI 组件

结构重构后的组件体系：
- StepCard       步骤卡片：序号徽章 + 标题 + 说明 + 内容区（替代 QGroupBox 堆叠）
- AppSidebar     现代侧边导航：分组标签 + 模块项（序号徽章 + 名称 + 状态点）
- TagLabel       状态徽章标签（ok / error / running / muted）
"""

from PyQt6.QtWidgets import (QFrame, QLabel, QWidget, QVBoxLayout, QHBoxLayout,
                             QFormLayout, QToolButton, QSizePolicy)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from gui.i18n import tr


# ── 步骤卡片 ────────────────────────────────────────────────────────────────
class StepCard(QFrame):
    """步骤卡片：序号徽章 + 标题 + 说明 + 内容区。

    取代旧的 QGroupBox 卡片：统一间距、圆角、标题层级，主操作按钮置于内容区。
    """

    def __init__(self, index, title: str, subtitle: str = "",
                 layout_kind: str = "form", parent=None):
        super().__init__(parent)
        self.setObjectName("stepCard")

        v = QVBoxLayout(self)
        v.setContentsMargins(18, 14, 18, 16)
        v.setSpacing(12)

        # ── 头部：序号徽章 + 标题列 ──
        header = QHBoxLayout()
        header.setSpacing(12)

        badge = QLabel(str(index))
        badge.setObjectName("stepIndex")
        badge.setFixedSize(28, 28)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont()
        f.setBold(True)
        f.setPointSize(10)
        badge.setFont(f)
        if str(index) == "":
            badge.setVisible(False)

        tcol = QVBoxLayout()
        tcol.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("stepTitle")
        tcol.addWidget(title_lbl)
        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setObjectName("stepSub")
            sub_lbl.setWordWrap(True)
            tcol.addWidget(sub_lbl)

        header.addWidget(badge)
        header.addLayout(tcol, stretch=1)
        v.addLayout(header)

        # ── 内容区 ──
        self.content = QWidget()
        if layout_kind == "form":
            self.content_layout = QFormLayout(self.content)
            self.content_layout.setContentsMargins(40, 0, 0, 0)
            self.content_layout.setVerticalSpacing(8)
            self.content_layout.setHorizontalSpacing(14)
            self.content_layout.setFieldGrowthPolicy(
                QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        else:
            self.content_layout = QVBoxLayout(self.content)
            self.content_layout.setContentsMargins(40, 0, 0, 0)
            self.content_layout.setSpacing(8)
        v.addWidget(self.content)

        # 行高随内容，序号徽章不拉伸
        badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def add_row(self, label: str, widget) -> None:
        """向内容区追加一行（仅 form 布局）"""
        if isinstance(self.content_layout, QFormLayout):
            self.content_layout.addRow(label, widget)
        else:
            self.content_layout.addWidget(widget)

    def add_widget(self, widget) -> None:
        """向内容区追加控件（vbox 布局用）"""
        self.content_layout.addWidget(widget)

    def add_layout(self, layout) -> None:
        """向内容区追加子布局"""
        self.content_layout.addLayout(layout)

    def add_stretch(self, stretch: int = 1) -> None:
        """内容区底部弹性占位"""
        self.content_layout.addStretch(stretch)


# ── 侧边导航 ────────────────────────────────────────────────────────────────
class SidebarItem(QToolButton):
    """导航模块项：序号徽章 + 名称 + 状态点。

    状态点（右侧圆点）反映该模块进度：
    - idle   灰
    - ready  绿（GROMACS 就绪模块）
    - wip    琥珀（开发中）
    """

    def __init__(self, index: str, title: str, status: str = "idle", parent=None):
        super().__init__(parent)
        self.setObjectName("navItem")
        self.setCheckable(True)
        self.setAutoRaise(True)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setText(f"{index}  {title}")
        self.setProperty("navStatus", status)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class AppSidebar(QWidget):
    """现代侧边导航：分组标签 + 模块项列表。"""

    currentChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._v = QVBoxLayout(self)
        self._v.setContentsMargins(12, 14, 12, 14)
        self._v.setSpacing(2)
        self._items = []

        # 底部弹性
        self._v.addStretch(1)

    def add_section(self, title: str) -> None:
        """添加分组标签"""
        lbl = QLabel(tr(title))
        lbl.setObjectName("navSection")
        self._v.insertWidget(max(0, self._v.count() - 1), lbl)

    def add_item(self, index: str, title: str, status: str = "idle") -> int:
        """添加模块项，返回其行号（用于 setCurrentRow）"""
        item = SidebarItem(index, tr(title), status)
        row = len(self._items)
        self._items.append(item)
        # 插到 stretch 之前
        self._v.insertWidget(max(0, self._v.count() - 1), item)
        item.clicked.connect(lambda: self.currentChanged.emit(row))
        return row

    def set_current(self, row: int) -> None:
        """设置当前选中项"""
        if 0 <= row < len(self._items):
            for i, it in enumerate(self._items):
                it.setChecked(i == row)

    def items(self):
        return self._items


# ── 状态徽章 ────────────────────────────────────────────────────────────────
class TagLabel(QLabel):
    """状态徽章：ok / error / running / muted，随主题自动换色。"""

    def __init__(self, text: str = "", role: str = "muted", parent=None):
        super().__init__(text, parent)
        self.setObjectName("tag")
        self.setProperty("role", role)
