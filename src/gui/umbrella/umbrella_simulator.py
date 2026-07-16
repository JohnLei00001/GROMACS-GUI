from PyQt6.QtWidgets import QTabWidget
from gui.umbrella.build_tab import BuildTab
from gui.umbrella.em_tab import EmTab
from gui.umbrella.nvt_tab import NvtTab
from gui.umbrella.npt_tab import NptTab
from gui.umbrella.pull_tab import PullTab
from gui.umbrella.window_tab import WindowTab
from gui.umbrella.batch_tab import BatchTab
from gui.umbrella.wham_tab import WhamTab

class UmbrellaSimulator(QTabWidget):
    """伞形取样 Pipeline：构建 → EM → NVT → NPT → Pull → 窗口 → 批量MD → WHAM"""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        # 1. 体系构建
        self.build_tab = BuildTab(main_window)
        self.addTab(self.build_tab, "1. 体系构建")

        # 2. EM
        self.em_tab = EmTab(main_window)
        self.addTab(self.em_tab, "2. EM")

        # 3. NVT
        self.nvt_tab = NvtTab(main_window)
        self.addTab(self.nvt_tab, "3. NVT")

        # 4. NPT
        self.npt_tab = NptTab(main_window)
        self.addTab(self.npt_tab, "4. NPT")

        # 5. Pull 模拟
        self.pull_tab = PullTab(main_window)
        self.addTab(self.pull_tab, "5. Pull 模拟")

        # 6. 窗口设置
        self.window_tab = WindowTab(main_window)
        self.addTab(self.window_tab, "6. 窗口设置")

        # 7. 批量 MD
        self.batch_tab = BatchTab(main_window)
        self.addTab(self.batch_tab, "7. 批量 MD")

        # 8. WHAM 分析
        self.wham_tab = WhamTab(main_window)
        self.addTab(self.wham_tab, "8. WHAM 分析")

        # 信号链
        self.build_tab.build_done.connect(self._on_build_done)
        self.em_tab.em_done.connect(self._on_em_done)
        self.nvt_tab.nvt_done.connect(self._on_nvt_done)
        self.npt_tab.npt_done.connect(self._on_npt_done)
        self.pull_tab.pull_done.connect(self._on_pull_done)
        self.window_tab.windows_ready.connect(self._on_windows_ready)
        self.batch_tab.batch_done.connect(self._on_batch_done)

    def _on_build_done(self, cwd):
        self.em_tab.update_cwd(cwd)
        self.nvt_tab.update_cwd(cwd)
        self.npt_tab.update_cwd(cwd)
        self.pull_tab.update_cwd(cwd)
        self.window_tab.update_cwd(cwd)
        self.setCurrentIndex(1)

    def _on_em_done(self, cwd):
        self.nvt_tab.update_cwd(cwd)
        self.setCurrentIndex(2)

    def _on_nvt_done(self, cwd):
        self.npt_tab.update_cwd(cwd)
        self.setCurrentIndex(3)

    def _on_npt_done(self, cwd):
        self.pull_tab.update_cwd(cwd)
        self.setCurrentIndex(4)

    def _on_pull_done(self, cwd):
        self.window_tab.update_cwd(cwd)
        self.setCurrentIndex(5)

    def _on_windows_ready(self, cwd, windows):
        self.batch_tab.update_windows(cwd, windows)
        self.wham_tab.update_data(cwd, windows)
        self.setCurrentIndex(6)

    def _on_batch_done(self, cwd):
        self.wham_tab.update_data(cwd, self.window_tab.windows)
        self.setCurrentIndex(7)
