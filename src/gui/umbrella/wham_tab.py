"""Umbrella WHAM Tab —— 汇总窗口数据 → PMF 曲线"""

from PyQt6.QtWidgets import (QFrame, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel,
                             QFormLayout, QLineEdit, QFileDialog,
                             QMessageBox)
from gui.i18n import tr, trf
from gui.theme import set_role
from gui.widgets import StepCard
from .workflow_context import UmbrellaContext
import os, shutil
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class WhamTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.ctx: UmbrellaContext = None
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget(); layout = QVBoxLayout(w); layout.setSpacing(10)

        self.status_label = QLabel(tr("等待批量 MD 完成..."))
        set_role(self.status_label, "muted")
        layout.addWidget(self.status_label)

        g1_card = StepCard("", tr("WHAM 参数"))
        f1 = g1_card.content_layout
        self.temp_input = QLineEdit("300")
        f1.addRow(tr("温度 (K):"), self.temp_input)
        self.bins_input = QLineEdit("200")
        f1.addRow(tr("直方图 bins:"), self.bins_input)
        self.tol_input = QLineEdit("1e-6")
        f1.addRow(tr("收敛容差:"), self.tol_input)

        self.btn_wham = QPushButton(tr("▶ 运行 WHAM 分析"))
        self.btn_wham.clicked.connect(self.run_wham)
        set_role(self.btn_wham, "primary")
        f1.addRow("", self.btn_wham)
        layout.addWidget(g1_card)

        g2_card = StepCard("", tr("PMF 曲线"), layout_kind="vbox")
        g2_layout = g2_card.content_layout
        self.canvas = FigureCanvas(Figure(figsize=(6, 4)))
        self.ax = self.canvas.figure.add_subplot(111)
        self.ax.set_xlabel("Reaction Coordinate (nm)")
        self.ax.set_ylabel("PMF (kJ/mol)")
        self.ax.grid(True, alpha=0.3)
        self.canvas.figure.tight_layout()
        g2_layout.addWidget(self.canvas)

        btn_save = QPushButton(tr("保存 PMF 数据"))
        btn_save.clicked.connect(self.save_pmf)
        set_role(btn_save, "primary")
        g2_layout.addWidget(btn_save)
        layout.addWidget(g2_card)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    def update_context(self, ctx: UmbrellaContext):
        self.ctx = ctx
        n = len(ctx.windows) if ctx.windows else 0
        self.status_label.setText(trf("{n} 个窗口 (目录: {dir})", n=n, dir=ctx.cwd))
        set_role(self.status_label, "ok")

    def run_wham(self):
        if not self.ctx or not self.ctx.windows:
            QMessageBox.warning(self, tr("警告"), tr("请先完成批量 MD"))
            return

        pullx_files = []
        missing = []
        for _, _, dir_name in self.ctx.windows:
            p = os.path.join(self.ctx.cwd, dir_name, "pullx.xvg")
            if os.path.exists(p):
                pullx_files.append(p)
            else:
                missing.append(dir_name)

        if missing:
            QMessageBox.warning(self, tr("警告"),
                trf("{n} 个窗口缺少 pullx.xvg: {missing}...",
                    n=len(missing), missing=', '.join(missing[:5])))
            return
        if len(pullx_files) < 2:
            QMessageBox.warning(self, tr("警告"), tr("至少需要 2 个窗口才能运行 WHAM"))
            return

        files_path = self.ctx.resolve("wham_files.txt")
        with open(files_path, "w") as f:
            for pf in pullx_files:
                f.write(pf + "\n")

        temp = self.temp_input.text()
        bins = self.bins_input.text()
        tol = self.tol_input.text()

        args = ["wham"]
        try:
            all_data = []
            for pf in pullx_files:
                with open(pf) as f:
                    for line in f:
                        if line.startswith(('#', '@')): continue
                        parts = line.split()
                        if len(parts) >= 2:
                            all_data.append(float(parts[1]))
            if all_data:
                dmin, dmax = min(all_data), max(all_data)
                margin = (dmax - dmin) * 0.1
                args.extend([str(dmin - margin), str(dmax + margin)])
            else:
                args.extend(["0", "5"])
        except:
            args.extend(["0", "5"])

        args.extend([str(bins), str(tol), str(temp), "0", "wham_result.xvg", "wham_histo.xvg"])
        args.extend(["-ix", files_path])

        self.btn_wham.setEnabled(False)
        self.main_window.log(tr(">>> 运行 WHAM 分析..."))
        self._start_worker(args, on_finish=lambda s, m: self._on_wham_done(s, m))

    def _on_wham_done(self, success, message):
        self.btn_wham.setEnabled(True)
        if not success:
            QMessageBox.critical(self, tr("错误"), trf("WHAM 失败:\n{msg}", msg=message))
            return
        self.main_window.log(tr(">>> WHAM 分析完成"))
        self._plot_pmf()
        QMessageBox.information(self, tr("完成"), tr("WHAM 分析完成！PMF 曲线已绘制。"))

    def _plot_pmf(self):
        pmf_path = self.ctx.resolve("wham_result.xvg")
        if not os.path.exists(pmf_path):
            return
        try:
            x, y = [], []
            with open(pmf_path) as f:
                for line in f:
                    if line.startswith(('#', '@')): continue
                    parts = line.split()
                    if len(parts) >= 2:
                        x.append(float(parts[0]))
                        y.append(float(parts[1]))
            if x:
                self.ax.clear()
                self.ax.plot(x, y, 'b-', linewidth=1.5)
                self.ax.set_xlabel("Reaction Coordinate (nm)")
                self.ax.set_ylabel("PMF (kJ/mol)")
                self.ax.grid(True, alpha=0.3)
                self.canvas.figure.tight_layout()
                self.canvas.draw()
        except Exception as e:
            self.main_window.log(trf("PMF 绘图失败: {err}", err=e))

    def save_pmf(self):
        pmf_path = self.ctx.resolve("wham_result.xvg")
        if not os.path.exists(pmf_path):
            QMessageBox.warning(self, tr("警告"), tr("未找到 wham_result.xvg"))
            return
        fname, _ = QFileDialog.getSaveFileName(self, tr("保存 PMF"), pmf_path, "All Files (*)")
        if fname:
            shutil.copy(pmf_path, fname)
            self.main_window.log(trf("PMF 已保存到 {path}", path=fname))

    def _start_worker(self, args, input_text=None, on_finish=None):
        w = self.runner.create_worker(args, cwd=self.ctx.cwd, input_text=input_text)
        w.output_signal.connect(self.main_window.log)
        if on_finish:
            w.finished_signal.connect(on_finish)
        w.start()
