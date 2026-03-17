from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QComboBox, QLineEdit, 
                             QMessageBox, QFileDialog, QTabWidget)
from PyQt6.QtCore import pyqtSignal
import os

from .ligand_prep_tab import LigandPrepTab
# 暂时复用 Solution Simulator 的标签页，未来需要扩展或继承
from gui.em_tab import EMTab
from gui.eq_tab import EQTab
from gui.md_tab import MDTab
from gui.analysis_tab import AnalysisTab
from gui.topology_tab import TopologyTab # 需要改造为支持 Complex 的版本

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
        
        # 2. 复合物拓扑 (Complex Topology) - 这里暂时用 placeholder，因为需要重写 TopologyTab
        # 我们先放一个简单的 TopologyTab 看看能否复用，但其实不能直接复用
        # 为了演示 Phase 2 的起点，我们先只放 Ligand Prep
        
        # 3. 能量最小化 (EM) - 复用 Solution Simulator 的逻辑
        # 注意：EMTab 依赖 main_window.solution_tabs.widget(0).cwd
        # 这里会报错，因為 LigandSimulator 不是 solution_tabs
        # 我们需要修改 EMTab 的 get_cwd 逻辑，或者在这里 mock 一个 solution_tabs
        
        # 暂时只添加配体准备页，明确告知用户正在开发中
        label = QLabel("后续步骤 (Complex Topology -> EM -> EQ -> MD) 将在 Phase 2 后续更新中实现。\n目前请先完成配体拓扑生成。")
        label.setStyleSheet("color: gray; font-style: italic; margin: 20px;")
        layout.addWidget(label)
