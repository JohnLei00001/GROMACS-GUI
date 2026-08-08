"""Umbrella Sampling Pipeline 协调器

5 步 Pipeline：构建 → 平衡(EM+NVT+NPT) → Pull → 窗口+批量MD → WHAM

页面由 MainWindow 注入统一的页签栏（与其他 Pipeline 共享同一 QTabWidget），
保证切换模块时右侧页签栏完全对齐。
"""

from PyQt6.QtWidgets import QWidget, QTabWidget
from gui.i18n import tr, trf
from gui.umbrella.build_tab import BuildTab
from gui.umbrella.equilibration_tab import EquilibrationTab
from gui.umbrella.pull_tab import PullTab
from gui.umbrella.window_tab import WindowTab
from gui.umbrella.batch_tab import BatchTab
from gui.umbrella.wham_tab import WhamTab
from .workflow_context import UmbrellaContext


class UmbrellaSimulator(QWidget):
    """伞形取样 Pipeline：构建 → 平衡 → Pull → 窗口+批量MD → WHAM（纯容器 + 懒加载）"""

    def __init__(self, main_window):
        super().__init__(main_window)   # 以主窗口为父，避免成为独立顶层窗口导致闪窗
        self.main_window = main_window
        self._built = False

    def ensure_built(self, tabs: QTabWidget):
        """确保页面已构建（懒加载），页面直接以页签栏为父避免闪窗"""
        if self._built:
            return
        self._built = True
        self.build_tab = BuildTab(main_window=self.main_window, parent=tabs)
        tabs.addTab(self.build_tab, tr("1. 体系构建"))

        self.eq_tab = EquilibrationTab(self.main_window, tabs)
        tabs.addTab(self.eq_tab, tr("2. 平衡 (EM+NVT+NPT)"))

        self.pull_tab = PullTab(self.main_window, tabs)
        tabs.addTab(self.pull_tab, tr("3. Pull 模拟"))

        self.window_tab = WindowTab(self.main_window, tabs)
        tabs.addTab(self.window_tab, tr("4. 窗口设置"))

        self.batch_tab = BatchTab(self.main_window, tabs)
        tabs.addTab(self.batch_tab, tr("5. 批量 MD"))

        self.wham_tab = WhamTab(self.main_window, tabs)
        tabs.addTab(self.wham_tab, tr("6. WHAM 分析"))

        # ── 信号链 ──
        self.build_tab.build_done.connect(self._on_build_done)
        self.eq_tab.eq_done.connect(self._on_eq_done)
        self.pull_tab.pull_done.connect(self._on_pull_done)
        self.window_tab.windows_ready.connect(self._on_windows_ready)
        self.batch_tab.batch_done.connect(self._on_batch_done)

    def _on_build_done(self, ctx: UmbrellaContext):
        self.main_window.log(trf(">>> [Pipeline] 体系构建完成 → {dir}", dir=ctx.cwd))
        self.eq_tab.update_context(ctx)
        self.main_window._set_pipeline_tab(2, 1)

    def _on_eq_done(self, ctx: UmbrellaContext):
        self.main_window.log(tr(">>> [Pipeline] 平衡阶段完成 → Pull"))
        self.pull_tab.update_context(ctx)
        self.main_window._set_pipeline_tab(2, 2)

    def _on_pull_done(self, ctx: UmbrellaContext):
        self.main_window.log(tr(">>> [Pipeline] Pull 完成 → 窗口设置"))
        self.window_tab.update_context(ctx)
        self.main_window._set_pipeline_tab(2, 3)

    def _on_windows_ready(self, ctx: UmbrellaContext):
        self.main_window.log(trf(">>> [Pipeline] {n} 个窗口就绪 → 批量 MD", n=len(ctx.windows)))
        self.batch_tab.update_context(ctx)
        self.wham_tab.update_context(ctx)
        self.main_window._set_pipeline_tab(2, 4)

    def _on_batch_done(self, ctx: UmbrellaContext):
        self.main_window.log(tr(">>> [Pipeline] 批量 MD 完成 → WHAM"))
        self.wham_tab.update_context(ctx)
        self.main_window._set_pipeline_tab(2, 5)
