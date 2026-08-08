from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTextEdit,
                             QLabel, QTabWidget, QMessageBox,
                             QStackedWidget, QFileDialog, QSplitter, QToolButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import os
import sys
import platform
import datetime

# 导入 GROMACS 运行器
from core.runner import GromacsRunner
from core.config import needs_configuration, save_gmx_path, get_setting
from gui.theme import apply_theme, set_role, get_mode, set_mode
from gui.i18n import tr, trf, get_language, set_language, retranslate_tree
from gui.widgets import AppSidebar
from gui.topology_tab import TopologyTab
from gui.em_tab import EMTab
from gui.eq_tab import EQTab
from gui.md_tab import MDTab
from gui.ligand.ligand_simulator import LigandSimulator
from gui.umbrella.umbrella_simulator import UmbrellaSimulator
from gui.analysis_tab import AnalysisTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GROMACS GUI")
        self.resize(1080, 760)

        self.runner = GromacsRunner()

        # 首次启动：自动检测或手动配置 GROMACS 路径
        self._ensure_gmx_configured()

        # ── 顶层布局：应用栏 + 内容行 + 状态栏 ──
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.root_layout = QVBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self._build_top_bar()

        # 主内容行：侧边导航 | 工作区
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.root_layout.addLayout(self.main_layout, stretch=1)

        self._build_sidebar()
        self._build_workspace()
        self._build_log_panel()
        self._setup_statusbar()

    # ═══ 顶部应用栏 ═══════════════════════════════════════════════════════
    def _build_top_bar(self):
        bar = QWidget()
        bar.setObjectName("topBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(18, 8, 18, 8)
        lay.setSpacing(10)

        title = QLabel("GROMACS GUI")
        title.setObjectName("appTitle")
        lay.addWidget(title)
        lay.addStretch()

        # 环境状态徽章（右侧常驻）
        self.status_env_dot = QLabel()
        self.status_env_dot.setObjectName("tag")
        lay.addWidget(self.status_env_dot)

        self.btn_theme = QToolButton()
        self.btn_theme.setObjectName("topBtn")
        self.btn_theme.setToolTip(tr("切换主题（亮 / 暗）"))
        self.btn_theme.clicked.connect(self._toggle_theme)
        lay.addWidget(self.btn_theme)

        self.btn_lang = QToolButton()
        self.btn_lang.setObjectName("topBtn")
        self.btn_lang.setToolTip(tr("切换界面语言（中文 / English）"))
        self.btn_lang.clicked.connect(self._toggle_language)
        lay.addWidget(self.btn_lang)

        self.root_layout.insertWidget(0, bar)
        self._refresh_top_buttons()
        self._refresh_gmx_status()

    # ═══ 侧边导航 ═════════════════════════════════════════════════════════
    def _build_sidebar(self):
        self.sidebar = AppSidebar()
        self.sidebar.setFixedWidth(224)
        self.main_layout.addWidget(self.sidebar)

        self.sidebar.add_section("模拟工作流")
        nav_specs = [
            ("01", "溶液体系模拟", "ready"),
            ("02", "蛋白-配体复合物模拟", "ready"),
            ("03", "伞形取样自由能计算", "ready"),
            ("04", "聚合物模拟（开发中）", "wip"),
        ]
        self._nav_rows = [self.sidebar.add_item(n, t, s) for n, t, s in nav_specs]
        self.sidebar.currentChanged.connect(self._on_nav_changed)

    # ═══ 工作区 ═══════════════════════════════════════════════════════════
    def _build_workspace(self):
        self.workspace = QWidget()
        ws_layout = QVBoxLayout(self.workspace)
        ws_layout.setContentsMargins(20, 16, 20, 0)
        ws_layout.setSpacing(0)
        self.main_layout.addWidget(self.workspace, stretch=1)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        ws_layout.addWidget(self.splitter)

        # 顶部 StackedWidget 用于切换不同的 Builder
        self.stacked_widget = QStackedWidget()
        self.splitter.addWidget(self.stacked_widget)

        # --- 模块 1: Solution Simulator ---
        self.solution_tabs = QTabWidget()
        self.stacked_widget.addWidget(self.solution_tabs)

        # --- 模块 2: Ligand Simulator ---
        self.ligand_simulator = LigandSimulator(self)
        self.stacked_widget.addWidget(self.ligand_simulator)

        # --- 模块 3: Umbrella Sampling ---
        self.umbrella_simulator = UmbrellaSimulator(self)
        self.stacked_widget.addWidget(self.umbrella_simulator)

        # --- 模块 4: 占位符 (WIP) ---
        self.setup_wip_module(tr("Polymer Simulator 正在开发中...\n\n敬请期待！"))

        # 初始化 Solution Simulator 的各个功能标签页
        self.init_topology_tab()
        self.init_em_tab()
        self.init_eq_tab()
        self.init_md_tab()
        self.init_analysis_tab()

        # 默认选中第一项
        self.sidebar.set_current(0)
        self.stacked_widget.setCurrentIndex(0)

    # ═══ 日志面板 ═════════════════════════════════════════════════════════
    def _build_log_panel(self):
        self.log_widget = QWidget()
        log_layout = QVBoxLayout(self.log_widget)
        log_layout.setContentsMargins(0, 12, 0, 8)
        log_layout.setSpacing(6)

        # 日志标题行：标题 + 状态 + 清空 + 折叠
        log_header = QHBoxLayout()
        log_title = QLabel(tr("运行日志"))
        log_title.setObjectName("stepTitle")
        self.log_count_label = QLabel()
        self.log_count_label.setObjectName("stepSub")
        btn_clear = QPushButton(tr("清空"))
        btn_clear.setProperty("role", "ghost")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.clicked.connect(self.clear_log)

        self.btn_toggle_log = QToolButton()
        self.btn_toggle_log.setText(tr("▼ 收起"))
        self.btn_toggle_log.setToolTip(tr("展开 / 收起日志面板"))
        self.btn_toggle_log.setCheckable(True)
        self.btn_toggle_log.setChecked(True)
        self.btn_toggle_log.setAutoRaise(True)
        self.btn_toggle_log.clicked.connect(self.toggle_log)

        log_header.addWidget(log_title)
        log_header.addWidget(self.log_count_label)
        log_header.addStretch()
        log_header.addWidget(btn_clear)
        log_header.addWidget(self.btn_toggle_log)
        log_layout.addLayout(log_header)

        self.log_output = QTextEdit()
        self.log_output.setObjectName("logOutput")
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output, stretch=1)

        # 测试 GROMACS 按钮
        self.btn_test = QPushButton(tr("测试 GROMACS 环境"))
        self.btn_test.clicked.connect(self.test_gmx)
        log_layout.addWidget(self.btn_test)

        self.splitter.addWidget(self.log_widget)

        # 防止用户拖动分割条时把日志面板彻底拖没（拖没后无法恢复）
        self.splitter.setCollapsible(1, False)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([560, 160])
        self._log_visible = True
        self._log_last_height = 160
        self._log_entries = 0
        self._refresh_log_count()

    # ═══ 状态栏 ═══════════════════════════════════════════════════════════
    def _setup_statusbar(self):
        sb = self.statusBar()
        sb.showMessage(tr("工作目录: 未设置"))

    # ── 顶栏按钮 ──────────────────────────────────────────────────────────
    def _refresh_top_buttons(self):
        if get_mode() == "light":
            self.btn_theme.setText("☀️ " + tr("亮色"))
        else:
            self.btn_theme.setText("🌙 " + tr("深色"))
        self.btn_lang.setText("EN" if get_language() == "zh" else "中文")

    def _toggle_theme(self):
        new_mode = "light" if get_mode() == "dark" else "dark"
        set_mode(new_mode)
        from core.config import save_setting
        save_setting("theme", new_mode)
        from PyQt6.QtWidgets import QApplication
        apply_theme(QApplication.instance())
        self._refresh_top_buttons()
        self._refresh_gmx_status()

    def _toggle_language(self):
        new_lang = "en" if get_language() == "zh" else "zh"
        set_language(new_lang)
        retranslate_tree(self)
        self._refresh_top_buttons()
        self._refresh_log_buttons()
        self._refresh_gmx_status()
        self._update_status_cwd()

    def _refresh_log_buttons(self):
        if getattr(self, "_log_visible", True):
            self.btn_toggle_log.setText(tr("▼ 收起"))
        else:
            self.btn_toggle_log.setText(tr("▲ 展开日志"))

    # ── GROMACS 状态徽章 ──────────────────────────────────────────────────
    def _refresh_gmx_status(self):
        if not hasattr(self, "status_env_dot"):
            return
        if self.runner.is_ready():
            self.status_env_dot.setText(tr("● GROMACS 就绪"))
            self.status_env_dot.setProperty("role", "ok")
        else:
            self.status_env_dot.setText(tr("○ GROMACS 未配置"))
            self.status_env_dot.setProperty("role", "error")
        self.status_env_dot.style().unpolish(self.status_env_dot)
        self.status_env_dot.style().polish(self.status_env_dot)

    # ── 导航 ──────────────────────────────────────────────────────────────
    def _on_nav_changed(self, index: int):
        self.stacked_widget.setCurrentIndex(index)
        self._update_status_cwd()

    def _update_status_cwd(self):
        try:
            idx = self.stacked_widget.currentIndex()
            cwd = None
            if idx == 0:
                cwd = self.solution_tabs.widget(0).cwd
            elif idx == 1:
                cwd = self.ligand_simulator.prep_tab.cwd
            if cwd:
                self.statusBar().showMessage(trf("工作目录: {cwd}", cwd=cwd))
                return
        except Exception:
            pass
        self.statusBar().showMessage(tr("工作目录: 未设置"))

    # ── 日志 ──────────────────────────────────────────────────────────────
    def log(self, message):
        """向日志窗口输出带时间戳的信息"""
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{ts}] {message}")
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum())
        self._log_entries += 1
        self._refresh_log_count()

    def clear_log(self):
        self.log_output.clear()
        self._log_entries = 0
        self._refresh_log_count()

    def _refresh_log_count(self):
        if hasattr(self, "log_count_label"):
            self.log_count_label.setText(trf("共 {n} 条", n=self._log_entries))

    def toggle_log(self):
        sizes = self.splitter.sizes()
        if self._log_visible:
            if len(sizes) > 1:
                self._log_last_height = sizes[1]
            self._log_visible = False
            self.log_output.setVisible(False)
            self.btn_test.setVisible(False)
            self.btn_toggle_log.setText(tr("▲ 展开日志"))
            total = sum(sizes)
            self.splitter.setSizes([max(240, total - 30), 30])
        else:
            self._log_visible = True
            self.log_output.setVisible(True)
            self.btn_test.setVisible(True)
            self.btn_toggle_log.setText(tr("▼ 收起日志"))
            total = sum(sizes)
            h = max(self._log_last_height, 100)
            self.splitter.setSizes([max(240, total - h), h])

    # ── GROMACS 环境 ──────────────────────────────────────────────────────
    def test_gmx(self):
        if not self.runner.is_ready():
            QMessageBox.warning(self, tr("未配置"), tr("GROMACS 路径未设置，请先配置。"))
            self._configure_gmx_path()
            return
        self.log(trf("\n>>> 正在运行: gmx {cmd}", cmd="-version"))
        success, output = self.runner.run_command(['-version'])
        self.log(output)
        if success:
            QMessageBox.information(self, tr("成功"), tr("GROMACS 运行正常！"))
        else:
            QMessageBox.critical(self, tr("错误"), trf("GROMACS 运行失败，请检查路径。\n\n{output}", output=output))
        self._refresh_gmx_status()

    # ── 模块构建 ──────────────────────────────────────────────────────────
    def setup_wip_module(self, text):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addStretch()
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(13)
        label.setFont(font)
        set_role(label, "muted")
        layout.addWidget(label)
        layout.addStretch()
        self.stacked_widget.addWidget(widget)

    def init_topology_tab(self):
        tab = TopologyTab(self)
        self.solution_tabs.addTab(tab, tr("1. 拓扑与水箱"))

    def init_em_tab(self):
        tab = EMTab(self)
        self.solution_tabs.addTab(tab, tr("2. 能量最小化"))

    def init_eq_tab(self):
        tab = EQTab(self)
        self.solution_tabs.addTab(tab, tr("3. 系统平衡"))

    def init_md_tab(self):
        tab = MDTab(self)
        self.solution_tabs.addTab(tab, tr("4. 生产模拟"))

    def init_analysis_tab(self):
        tab = AnalysisTab(self)
        self.solution_tabs.addTab(tab, tr("5. 分析与可视化"))

    # ── GROMACS 配置 ──────────────────────────────────────────────────────
    def _ensure_gmx_configured(self):
        if not self.runner.is_ready():
            self._configure_gmx_path()

    def _configure_gmx_path(self):
        is_windows = platform.system() == "Windows"
        if is_windows:
            file_filter = tr("GROMACS 可执行文件 (gmx.exe);;所有文件 (*.*)")
        else:
            file_filter = tr("所有文件 (*)")

        example = (tr("  Windows 示例: C:\\Gromacs\\bin\\gmx.exe") if is_windows else
                   tr("  Linux 示例: /usr/local/gromacs/bin/gmx"))

        msg = trf(
            "未检测到 GROMACS 可执行文件。\n\n请选择 gmx 可执行文件：\n{example}\n\n如已添加到 PATH 环境变量，可在终端中运行 'which gmx' 或 'where gmx' 查看路径。",
            example=example,
        )

        QMessageBox.information(self, tr("首次配置"), msg)

        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("选择 GROMACS 可执行文件 (gmx)"),
            "",
            file_filter
        )

        if path:
            save_gmx_path(path)
            self.runner.update_path()
            self.log(trf("[系统] GROMACS 路径已配置: {path}", path=path))
        else:
            self.log(tr("[系统] 警告：未配置 GROMACS 路径，部分功能不可用。\n       可稍后点击「测试 GROMACS 环境」按钮重新配置。"))
        self._refresh_gmx_status()
        self._update_status_cwd()
