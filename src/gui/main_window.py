from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, 
                             QLabel, QTabWidget, QMessageBox)
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
        
        # 主布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # 顶部标签页
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs, stretch=2)
        
        # 初始化各个功能标签页
        self.init_topology_tab()
        self.init_em_tab()
        self.init_eq_tab()
        self.init_md_tab()
        self.init_analysis_tab()
        
        # 底部日志输出窗口
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas;")
        
        log_label = QLabel("GROMACS 日志输出:")
        log_label.setStyleSheet("font-weight: bold;")
        
        self.layout.addWidget(log_label)
        self.layout.addWidget(self.log_output, stretch=1)
        
        self.log(f"系统初始化完成。GROMACS路径: {self.runner.gmx_path}")

    def init_topology_tab(self):
        tab = TopologyTab(self)
        self.tabs.addTab(tab, "1. 拓扑与水箱")
        
    def init_em_tab(self):
        tab = EMTab(self)
        self.tabs.addTab(tab, "2. 能量最小化")
        
    def init_eq_tab(self):
        tab = EQTab(self)
        self.tabs.addTab(tab, "3. 系统平衡")
        
    def init_md_tab(self):
        tab = MDTab(self)
        self.tabs.addTab(tab, "4. 生产模拟")
        
    def init_analysis_tab(self):
        tab = AnalysisTab(self)
        self.tabs.addTab(tab, "5. 分析与可视化")
        
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
