from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QComboBox, QLineEdit, 
                             QMessageBox, QFileDialog, QTabWidget)
from PyQt6.QtCore import pyqtSignal
import os

from .ligand_prep_tab import LigandPrepTab
from .complex_tab import ComplexTab

# 暂时复用 Solution Simulator 的标签页，未来需要扩展或继承
from gui.em_tab import EMTab
from gui.eq_tab import EQTab
from gui.md_tab import MDTab
from gui.analysis_tab import AnalysisTab

class LigandSimulator(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.cwd = os.getcwd()
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 使用 TabWidget 管理流程
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # 1. 配体准备 (Ligand Prep)
        self.prep_tab = LigandPrepTab(self.main_window)
        self.tabs.addTab(self.prep_tab, "1. 配体准备")
        
        # 2. 复合物拓扑 (Complex Topology)
        self.complex_tab = ComplexTab(self.main_window)
        self.tabs.addTab(self.complex_tab, "2. 复合物拓扑与水箱")
        
        # 连接信号：当配体准备完成时，更新 ComplexTab 的状态
        self.prep_tab.topology_ready.connect(self.complex_tab.update_ligand_info)
        
        # 3. 能量最小化 (EM)
        self.em_tab = EMTab(self.main_window)
        self.tabs.addTab(self.em_tab, "3. 能量最小化")
        
        # 4. 系统平衡 (EQ)
        self.eq_tab = EQTab(self.main_window)
        self.tabs.addTab(self.eq_tab, "4. 系统平衡")
        
        # 5. 生产模拟 (MD)
        self.md_tab = MDTab(self.main_window)
        self.tabs.addTab(self.md_tab, "5. 生产模拟")
        
        # 6. 分析与可视化
        self.analysis_tab = AnalysisTab(self.main_window)
        self.tabs.addTab(self.analysis_tab, "6. 分析与可视化")



