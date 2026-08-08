from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, 
                             QLabel, QTabWidget, QMessageBox, QListWidget, QListWidgetItem,
                             QStackedWidget, QFileDialog, QSplitter, QToolButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import os
import sys
import platform

# 导入 GROMACS 运行器
from core.runner import GromacsRunner
from core.config import needs_configuration, save_gmx_path
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
        self.resize(1000, 750)
        
        self.runner = GromacsRunner()
        
        # 首次启动：自动检测或手动配置 GROMACS 路径
        self._ensure_gmx_configured()
        
        # 主布局: 水平分割 (左侧导航, 右侧内容)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # === 左侧导航栏 ===
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        self.nav_list.setFixedWidth(210)
        nav_font = QFont()
        nav_font.setPointSize(10)
        self.nav_list.setFont(nav_font)

        # 导航项（序号前缀帮助用户建立流程心智模型）
        nav_items = [
            ("01", "Solution Simulator", "溶液体系模拟"),
            ("02", "Ligand Simulator", "蛋白-配体复合物模拟"),
            ("03", "Umbrella Sampling", "伞形取样自由能计算"),
            ("04", "Polymer Simulator", "聚合物模拟（开发中）"),
        ]
        for num, name, desc in nav_items:
            item = QListWidgetItem(f"  {num}  {name}")
            item.setToolTip(desc)
            self.nav_list.addItem(item)

        self.main_layout.addWidget(self.nav_list)
        
        # === 右侧主体区域（QSplitter 可拖拽调整上下比例） ===
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.right_widget, stretch=1)
        
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_layout.addWidget(self.splitter)
        
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
        self.setup_wip_module("Polymer Simulator 正在开发中...\n\n敬请期待！")
        
        # 连接导航点击事件
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        
        # 初始化 Solution Simulator 的各个功能标签页
        self.init_topology_tab()
        self.init_em_tab()
        self.init_eq_tab()
        self.init_md_tab()
        self.init_analysis_tab()
        
        # 默认选中第一项
        self.nav_list.setCurrentRow(0)
        
        # 底部日志输出窗口 (全局共享, 可折叠)
        self.log_widget = QWidget()
        log_layout = QVBoxLayout(self.log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(4)

        # 日志标题行：标题 + 折叠按钮
        log_header = QHBoxLayout()
        log_title = QLabel("全局运行日志")
        log_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #8a8a8a;")
        self.btn_toggle_log = QToolButton()
        self.btn_toggle_log.setText("▼ 收起")
        self.btn_toggle_log.setToolTip("展开 / 收起日志面板")
        self.btn_toggle_log.setCheckable(True)
        self.btn_toggle_log.setChecked(True)
        self.btn_toggle_log.setAutoRaise(True)
        self.btn_toggle_log.clicked.connect(self.toggle_log)
        log_header.addWidget(log_title)
        log_header.addStretch()
        log_header.addWidget(self.btn_toggle_log)
        log_layout.addLayout(log_header)

        self.log_output = QTextEdit()
        self.log_output.setObjectName("logOutput")
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output, stretch=1)
        
        # 测试GROMACS按钮
        self.btn_test = QPushButton("测试 GROMACS 环境")
        self.btn_test.clicked.connect(self.test_gmx)
        log_layout.addWidget(self.btn_test)
        
        self.splitter.addWidget(self.log_widget)
        
        # 设置初始比例（上 75% : 下 25%）
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        self._log_visible = True

        # 状态栏：环境状态 + 当前工作目录
        self._setup_statusbar()

    def setup_wip_module(self, text):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        label.setFont(font)
        layout.addWidget(label)
        self.stacked_widget.addWidget(widget)

    # ── 导航 ────────────────────────────────────────────────────────────────
    def _on_nav_changed(self, index: int):
        """导航切换：切换模块并更新状态栏工作目录"""
        self.stacked_widget.setCurrentIndex(index)
        self._update_status_cwd()

    def _update_status_cwd(self):
        """根据当前模块显示工作目录"""
        try:
            idx = self.stacked_widget.currentIndex()
            cwd = None
            if idx == 0:
                cwd = self.solution_tabs.widget(0).cwd
            elif idx == 1:
                cwd = self.ligand_simulator.prep_tab.cwd
            if cwd:
                self.statusBar().showMessage(f"工作目录: {cwd}")
                return
        except Exception:
            pass
        self.statusBar().showMessage("工作目录: 未设置")

    # ── 状态栏 ──────────────────────────────────────────────────────────────
    def _setup_statusbar(self):
        """状态栏：左侧工作目录，右侧 GROMACS 环境状态"""
        sb = self.statusBar()
        sb.showMessage("工作目录: 未设置")

        # 环境状态徽标
        self.status_env_dot = QLabel()
        self.status_env_dot.setStyleSheet("font-size: 13px;")
        sb.addPermanentWidget(self.status_env_dot)
        self._refresh_gmx_status()

    def _refresh_gmx_status(self):
        """刷新 GROMACS 环境状态徽标"""
        if not hasattr(self, "status_env_dot"):
            return
        if self.runner.is_ready():
            dot, color, txt = "●", "#89d185", " GROMACS 就绪"
        else:
            dot, color, txt = "○", "#f48771", " GROMACS 未配置"
        self.status_env_dot.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: bold; padding-right: 12px;")
        self.status_env_dot.setText(dot + txt)

    # ── 日志折叠 ────────────────────────────────────────────────────────────
    def toggle_log(self):
        """展开 / 收起底部日志面板"""
        self._log_visible = not self._log_visible
        self.log_widget.setVisible(self._log_visible)
        self.btn_toggle_log.setText("▼ 收起" if self._log_visible else "▲ 展开")

    def log(self, message):
        """向日志窗口输出信息"""
        self.log_output.append(message)
        # 滚动到底部
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

    def test_gmx(self):
        """测试GROMACS是否可用"""
        if not self.runner.is_ready():
            QMessageBox.warning(self, "未配置", "GROMACS 路径未设置，请先配置。")
            self._configure_gmx_path()
            return
        self.log("\n>>> 正在运行: gmx -version")
        success, output = self.runner.run_command(['-version'])
        self.log(output)
        if success:
            QMessageBox.information(self, "成功", "GROMACS 运行正常！")
        else:
            QMessageBox.critical(self, "错误", f"GROMACS 运行失败，请检查路径。\n\n{output}")
        self._refresh_gmx_status()

    def init_topology_tab(self):
        tab = TopologyTab(self)
        self.solution_tabs.addTab(tab, "1. 拓扑与水箱")
        
    def init_em_tab(self):
        tab = EMTab(self)
        self.solution_tabs.addTab(tab, "2. 能量最小化")
        
    def init_eq_tab(self):
        tab = EQTab(self)
        self.solution_tabs.addTab(tab, "3. 系统平衡")
        
    def init_md_tab(self):
        tab = MDTab(self)
        self.solution_tabs.addTab(tab, "4. 生产模拟")
        
    def init_analysis_tab(self):
        tab = AnalysisTab(self)
        self.solution_tabs.addTab(tab, "5. 分析与可视化")

    def _ensure_gmx_configured(self):
        """确保 GROMACS 路径已配置，未配置则引导用户设置"""
        if not self.runner.is_ready():
            self._configure_gmx_path()

    def _configure_gmx_path(self):
        """弹出对话框让用户选择 GROMACS 可执行文件路径"""
        is_windows = platform.system() == "Windows"
        if is_windows:
            file_filter = "GROMACS 可执行文件 (gmx.exe);;所有文件 (*.*)"
        else:
            file_filter = "所有文件 (*)"

        msg = (
            "未检测到 GROMACS 可执行文件。\n\n"
            "请选择 gmx 可执行文件：\n"
            + ("  Windows 示例: C:\\Gromacs\\bin\\gmx.exe\n" if is_windows else
               "  Linux 示例: /usr/local/gromacs/bin/gmx\n")
            + "\n如已添加到 PATH 环境变量，可在终端中运行 'which gmx' 或 'where gmx' 查看路径。"
        )

        QMessageBox.information(self, "首次配置", msg)

        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 GROMACS 可执行文件 (gmx)",
            "",
            file_filter
        )

        if path:
            save_gmx_path(path)
            self.runner.update_path()
            self.log(f"[系统] GROMACS 路径已配置: {path}")
        else:
            self.log("[系统] 警告：未配置 GROMACS 路径，部分功能不可用。\n"
                      "       可稍后点击「测试 GROMACS 环境」按钮重新配置。")
        self._refresh_gmx_status()
        self._update_status_cwd()
