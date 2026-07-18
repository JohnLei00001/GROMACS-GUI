"""Umbrella Sampling Pipeline 协调器

5 步 Pipeline：构建 → 平衡(EM+NVT+NPT) → Pull → 窗口+批量MD → WHAM
"""

from PyQt6.QtWidgets import QTabWidget
from gui.umbrella.build_tab import BuildTab
from gui.umbrella.equilibration_tab import EquilibrationTab
from gui.umbrella.pull_tab import PullTab
from gui.umbrella.window_tab import WindowTab
from gui.umbrella.batch_tab import BatchTab
from gui.umbrella.wham_tab import WhamTab
from .workflow_context import UmbrellaContext


class UmbrellaSimulator(QTabWidget):
    """伞形取样 Pipeline：构建 → 平衡 → Pull → 窗口+批量MD → WHAM"""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        self.build_tab = BuildTab(main_window)
        self.addTab(self.build_tab, "1. 体系构建")

        self.eq_tab = EquilibrationTab(main_window)
        self.addTab(self.eq_tab, "2. 平衡 (EM+NVT+NPT)")

        self.pull_tab = PullTab(main_window)
        self.addTab(self.pull_tab, "3. Pull 模拟")

        self.window_tab = WindowTab(main_window)
        self.addTab(self.window_tab, "4. 窗口设置")

        self.batch_tab = BatchTab(main_window)
        self.addTab(self.batch_tab, "5. 批量 MD")

        self.wham_tab = WhamTab(main_window)
        self.addTab(self.wham_tab, "6. WHAM 分析")

        # ── 信号链 ──
        self.build_tab.build_done.connect(self._on_build_done)
        self.eq_tab.eq_done.connect(self._on_eq_done)
        self.pull_tab.pull_done.connect(self._on_pull_done)
        self.window_tab.windows_ready.connect(self._on_windows_ready)
        self.batch_tab.batch_done.connect(self._on_batch_done)

    def _on_build_done(self, ctx: UmbrellaContext):
        self.main_window.log(f">>> [Pipeline] 体系构建完成 → {ctx.cwd}")
        self.eq_tab.update_context(ctx)
        self.setCurrentIndex(1)

    def _on_eq_done(self, ctx: UmbrellaContext):
        self.main_window.log(">>> [Pipeline] 平衡阶段完成 → Pull")
        self.pull_tab.update_context(ctx)
        self.setCurrentIndex(2)

    def _on_pull_done(self, ctx: UmbrellaContext):
        self.main_window.log(">>> [Pipeline] Pull 完成 → 窗口设置")
        self.window_tab.update_context(ctx)
        self.setCurrentIndex(3)

    def _on_windows_ready(self, ctx: UmbrellaContext):
        self.main_window.log(f">>> [Pipeline] {len(ctx.windows)} 个窗口就绪 → 批量 MD")
        self.batch_tab.update_context(ctx)
        self.wham_tab.update_context(ctx)
        self.setCurrentIndex(4)

    def _on_batch_done(self, ctx: UmbrellaContext):
        self.main_window.log(">>> [Pipeline] 批量 MD 完成 → WHAM")
        self.wham_tab.update_context(ctx)
        self.setCurrentIndex(5)
