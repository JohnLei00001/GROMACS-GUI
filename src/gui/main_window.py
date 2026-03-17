from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, 
                             QLabel, QTabWidget, QMessageBox, QListWidget, QStackedWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import os
import sys

# 导入 GROMACS 运行器
from core.runner import GromacsRunner
from gui.topology_tab import TopologyTab
from gui.em_tab import EMTab
from gui.eq_tab import EQTab
from gui.md_tab import MDTab
from gui.analysis_tab import AnalysisTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GROMACS GUI")
        self.resize(1000, 750)
        
        self.runner = GromacsRunner()
        
        # 主布局: 水平分割 (左侧导航, 右侧内容)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # === 左侧导航栏 ===
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(200)
        nav_font = QFont()
        nav_font.setPointSize(10)
        self.nav_list.setFont(nav_font)
        
        # 美化左侧导航栏的样式 (深色主题)
        self.nav_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #3f3f3f;
                border-radius: 4px;
                outline: none;
                color: #d4d4d4;
            }
            QListWidget::item {
                padding: 12px 10px;
                border-bottom: 1px solid #3f3f3f;
            }
            QListWidget::item:selected {
                background-color: #005a9e;
                color: white;
                border-radius: 2px;
            }
            QListWidget::item:hover:!selected {
                background-color: #3f3f3f;
            }
        """)
        
        self.nav_list.addItem("Solution Simulator")
        self.nav_list.addItem("Ligand Simulator [WIP]")
        self.nav_list.addItem("Membrane Simulator [WIP]")
        self.nav_list.addItem("Polymer Simulator [WIP]")
        
        self.main_layout.addWidget(self.nav_list)
        
        # === 右侧主体区域 ===
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)
        self.main_layout.addWidget(self.right_widget, stretch=1)
        
        # 顶部 StackedWidget 用于切换不同的 Builder
        self.stacked_widget = QStackedWidget()
        self.right_layout.addWidget(self.stacked_widget, stretch=3)
        
        # --- 模块 1: Solution Simulator ---
        self.solution_tabs = QTabWidget()
        self.stacked_widget.addWidget(self.solution_tabs)
        
        # --- 模块 2,3,4: 占位符 (WIP) ---
        self.setup_wip_module("Protein-Ligand Complex Simulator 正在开发中...\n\n未来将支持自动处理配体拓扑 (如 ACPYPE 集成)")
        self.setup_wip_module("Membrane Simulator 正在开发中...\n\n未来将支持磷脂双分子层插入与定向")
        self.setup_wip_module("Polymer Simulator 正在开发中...\n\n敬请期待！")
        
        # 连接导航点击事件
        self.nav_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        
        # 初始化 Solution Simulator 的各个功能标签页
        self.init_topology_tab()
        self.init_em_tab()
        self.init_eq_tab()
        self.init_md_tab()
        self.init_analysis_tab()
        
        # 默认选中第一项
        self.nav_list.setCurrentRow(0)
        
        # 底部日志输出窗口 (全局共享)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas;")
        self.right_layout.addWidget(QLabel("全局运行日志:"))
        self.right_layout.addWidget(self.log_output, stretch=1)
        
        # 测试GROMACS按钮
        self.btn_test = QPushButton("测试 GROMACS 环境")
        self.btn_test.clicked.connect(self.test_gmx)
        self.right_layout.addWidget(self.btn_test)

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

    def log(self, message):
        """向日志窗口输出信息"""
        self.log_output.append(message)
        # 滚动到底部
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

    def test_gmx(self):
        """测试GROMACS是否可用"""
        self.log("\n>>> 正在运行: gmx -version")
        success, output = self.runner.run_command(['-version'])
        self.log(output)
        if success:
            QMessageBox.information(self, "成功", "GROMACS 运行正常！")
        else:
            QMessageBox.critical(self, "错误", "GROMACS 运行失败，请检查路径。")
