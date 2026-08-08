from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal
import os

from gui.i18n import tr, trf

from .ligand_prep_tab import LigandPrepTab
from .complex_tab import ComplexTab

# 暂时复用 Solution Simulator 的标签页，未来需要扩展或继承
from gui.em_tab import EMTab
from gui.eq_tab import EQTab
from gui.md_tab import MDTab
from gui.analysis_tab import AnalysisTab

class LigandSimulator(QWidget):
    """蛋白-配体复合物模拟：纯容器 + 懒加载。

    页面在首次切换到此模块时才构建（Lazy），
    减少启动与主题切换时需重绘的控件数量。
    """

    def __init__(self, main_window):
        super().__init__(main_window)   # 以主窗口为父，避免成为独立顶层窗口导致闪窗
        self.main_window = main_window
        self.runner = main_window.runner
        self.cwd = os.getcwd()
        self._built = False

    def ensure_built(self, tabs: "QTabWidget"):
        """确保页面已构建（懒加载），页面直接以页签栏为父避免闪窗"""
        if self._built:
            return
        self._built = True
        # 1. 配体准备 (Ligand Prep)
        self.prep_tab = LigandPrepTab(self.main_window, tabs)
        tabs.addTab(self.prep_tab, tr("1. 配体准备"))

        # 2. 复合物拓扑 (Complex Topology)
        self.complex_tab = ComplexTab(self.main_window, tabs)
        tabs.addTab(self.complex_tab, tr("2. 复合物拓扑与水箱"))

        # 连接信号：当配体准备完成时，更新 ComplexTab 的状态
        self.prep_tab.topology_ready.connect(self.complex_tab.update_ligand_info)

        # 3. 能量最小化 (EM)
        self.em_tab = EMTab(self.main_window, tabs)
        tabs.addTab(self.em_tab, tr("3. 能量最小化"))

        # 4. 系统平衡 (EQ)
        self.eq_tab = EQTab(self.main_window, tabs)
        tabs.addTab(self.eq_tab, tr("4. 系统平衡"))

        # 5. 生产模拟 (MD)
        self.md_tab = MDTab(self.main_window, tabs)
        tabs.addTab(self.md_tab, tr("5. 生产模拟"))

        # 6. 分析与可视化
        self.analysis_tab = AnalysisTab(self.main_window, tabs)
        tabs.addTab(self.analysis_tab, tr("6. 分析与可视化"))
