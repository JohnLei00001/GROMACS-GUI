"""Umbrella Batch Tab —— 批量执行伞形窗口 MD"""

from PyQt6.QtWidgets import (QFrame, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel,
                             QProgressBar, QListWidget, QListWidgetItem,
                             QMessageBox, QCheckBox)
from PyQt6.QtCore import pyqtSignal
from gui.i18n import tr, trf
from gui.theme import set_role
from gui.widgets import StepCard
from .workflow_context import UmbrellaContext
import os


class BatchTab(QWidget):
    batch_done = pyqtSignal(UmbrellaContext)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.ctx: UmbrellaContext = None
        self.current_index = 0
        self.running = False
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget(); layout = QVBoxLayout(w); layout.setSpacing(10)

        self.status_label = QLabel(tr("等待窗口配置完成..."))
        set_role(self.status_label, "muted")
        layout.addWidget(self.status_label)

        ctrl = QHBoxLayout()
        self.chk_skip_done = QCheckBox(tr("跳过已完成窗口"))
        self.chk_skip_done.setChecked(True)
        ctrl.addWidget(self.chk_skip_done)
        self.btn_run = QPushButton(tr("▶ 开始批量 MD"))
        self.btn_run.clicked.connect(self.start_batch)
        set_role(self.btn_run, "primary")
        ctrl.addWidget(self.btn_run)
        self.btn_stop = QPushButton(tr("⏹ 停止"))
        self.btn_stop.clicked.connect(self.stop_batch)
        self.btn_stop.setEnabled(False)
        ctrl.addWidget(self.btn_stop)
        layout.addLayout(ctrl)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        g_card = StepCard("", tr("窗口状态"), layout_kind="vbox")
        gl = g_card.content_layout
        self.win_list = QListWidget()
        gl.addWidget(self.win_list)
        layout.addWidget(g_card)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    def update_context(self, ctx: UmbrellaContext):
        self.ctx = ctx
        n = len(ctx.windows) if ctx.windows else 0
        self.status_label.setText(trf("{n} 个窗口已就绪 (目录: {dir})", n=n, dir=ctx.cwd))
        set_role(self.status_label, "ok")
        self._refresh_list()

    def _refresh_list(self):
        if not self.ctx:
            return
        self.win_list.clear()
        for i, (frame_d, ref_d, dir_name) in enumerate(self.ctx.windows):
            done = os.path.exists(os.path.join(self.ctx.cwd, dir_name, "umbrella.gro"))
            status = "✓" if done else "…"
            self.win_list.addItem(QListWidgetItem(f"  [{i:3d}] {dir_name}  ref={ref_d:.3f} nm  {status}"))

    def start_batch(self):
        if not self.ctx or not self.ctx.windows:
            return
        self.running = True
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.current_index = 0
        self.progress.setMaximum(len(self.ctx.windows))
        self._run_next()

    def stop_batch(self):
        self.running = False
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.main_window.log(tr(">>> 批量 MD 已停止"))

    def _run_next(self):
        if not self.running or not self.ctx:
            return
        if self.current_index >= len(self.ctx.windows):
            self._all_done()
            return

        _, ref_d, dir_name = self.ctx.windows[self.current_index]
        win_dir = os.path.join(self.ctx.cwd, dir_name)

        if self.chk_skip_done.isChecked() and os.path.exists(os.path.join(win_dir, "umbrella.gro")):
            self.main_window.log(trf(">>> [{i}/{total}] 跳过 {name} (已完成)",
                                     i=self.current_index+1, total=len(self.ctx.windows), name=dir_name))
            self.current_index += 1
            self._refresh_list()
            self.progress.setValue(self.current_index)
            self._run_next()
            return

        self.main_window.log(trf(">>> [{i}/{total}] 运行 {name} (ref={ref} nm)",
                                 i=self.current_index+1, total=len(self.ctx.windows),
                                 name=dir_name, ref=f"{ref_d:.3f}"))

        a1 = ["grompp", "-f", "umbrella.mdp", "-c", "npt.gro", "-p", "topol.top", "-o", "umbrella.tpr", "-maxwarn", "2"]
        w1 = self.runner.create_worker(a1, cwd=win_dir)
        w1.output_signal.connect(self.main_window.log)
        w1.finished_signal.connect(lambda s, m: self._on_grompp_done(s, m, win_dir))
        w1.start()

    def _on_grompp_done(self, success, message, win_dir):
        if not success:
            self.main_window.log(trf("  × grompp 失败: {msg}", msg=message[:200]))
            self.current_index += 1
            self.progress.setValue(self.current_index)
            self._refresh_list()
            self._run_next()
            return
        w2 = self.runner.create_worker(["mdrun", "-deffnm", "umbrella", "-v"], cwd=win_dir)
        w2.output_signal.connect(self.main_window.log)
        w2.finished_signal.connect(lambda s, m: self._on_window_done(s, m, win_dir))
        w2.start()

    def _on_window_done(self, success, message, win_dir):
        name = os.path.basename(win_dir)
        self.main_window.log(trf("  {mark} {name} {status}",
                                 mark='✓' if success else '×', name=name,
                                 status=tr("完成") if success else trf("失败: {msg}", msg=message[:200])))
        self.current_index += 1
        self.progress.setValue(self.current_index)
        self._refresh_list()
        self._run_next()

    def _all_done(self):
        self.running = False
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._refresh_list()
        done_count = sum(1 for _, _, dn in self.ctx.windows
                        if os.path.exists(os.path.join(self.ctx.cwd, dn, "umbrella.gro")))
        self.main_window.log(trf(">>> 批量 MD 完成 ({done}/{total} 窗口成功)",
                                 done=done_count, total=len(self.ctx.windows)))
        QMessageBox.information(self, tr("完成"),
            trf("批量 MD 完成！\n{done}/{total} 窗口成功。\n请继续到「WHAM 分析」。",
                done=done_count, total=len(self.ctx.windows)))
        self.batch_done.emit(self.ctx)
