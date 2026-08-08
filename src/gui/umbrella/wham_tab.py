"""Umbrella WHAM Tab —— 汇总窗口数据 → PMF 曲线"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel, QGroupBox,
                             QFormLayout, QLineEdit, QFileDialog,
                             QMessageBox)
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
        w = QWidget(); layout = QVBoxLayout(w)

        self.status_label = QLabel("等待批量 MD 完成...")
        self.status_label.setStyleSheet("color: #8a8a8a; font-weight: bold; font-size: 11pt;")
        layout.addWidget(self.status_label)

        g1 = QGroupBox("WHAM 参数")
        f1 = QFormLayout()
        self.temp_input = QLineEdit("300")
        f1.addRow("温度 (K):", self.temp_input)
        self.bins_input = QLineEdit("200")
        f1.addRow("直方图 bins:", self.bins_input)
        self.tol_input = QLineEdit("1e-6")
        f1.addRow("收敛容差:", self.tol_input)

        self.btn_wham = QPushButton("▶ 运行 WHAM 分析")
        self.btn_wham.clicked.connect(self.run_wham)
        f1.addRow("", self.btn_wham)
        g1.setLayout(f1)
        layout.addWidget(g1)

        g2 = QGroupBox("PMF 曲线")
        g2_layout = QVBoxLayout()
        self.canvas = FigureCanvas(Figure(figsize=(6, 4)))
        self.ax = self.canvas.figure.add_subplot(111)
        self.ax.set_xlabel("Reaction Coordinate (nm)")
        self.ax.set_ylabel("PMF (kJ/mol)")
        self.ax.grid(True, alpha=0.3)
        self.canvas.figure.tight_layout()
        g2_layout.addWidget(self.canvas)

        btn_save = QPushButton("保存 PMF 数据")
        btn_save.clicked.connect(self.save_pmf)
        g2_layout.addWidget(btn_save)
        g2.setLayout(g2_layout)
        layout.addWidget(g2)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    def update_context(self, ctx: UmbrellaContext):
        self.ctx = ctx
        n = len(ctx.windows) if ctx.windows else 0
        self.status_label.setText(f"{n} 个窗口 (目录: {ctx.cwd})")
        self.status_label.setStyleSheet("color: #89d185; font-weight: bold; font-size: 11pt;")

    def run_wham(self):
        if not self.ctx or not self.ctx.windows:
            QMessageBox.warning(self, "警告", "请先完成批量 MD")
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
            QMessageBox.warning(self, "警告",
                f"{len(missing)} 个窗口缺少 pullx.xvg: {', '.join(missing[:5])}...")
            return
        if len(pullx_files) < 2:
            QMessageBox.warning(self, "警告", "至少需要 2 个窗口才能运行 WHAM")
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
        self.main_window.log(">>> 运行 WHAM 分析...")
        self._start_worker(args, on_finish=lambda s, m: self._on_wham_done(s, m))

    def _on_wham_done(self, success, message):
        self.btn_wham.setEnabled(True)
        if not success:
            QMessageBox.critical(self, "错误", f"WHAM 失败:\n{message}")
            return
        self.main_window.log(">>> WHAM 分析完成")
        self._plot_pmf()
        QMessageBox.information(self, "完成", "WHAM 分析完成！PMF 曲线已绘制。")

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
            self.main_window.log(f"PMF 绘图失败: {e}")

    def save_pmf(self):
        pmf_path = self.ctx.resolve("wham_result.xvg")
        if not os.path.exists(pmf_path):
            QMessageBox.warning(self, "警告", "未找到 wham_result.xvg")
            return
        fname, _ = QFileDialog.getSaveFileName(self, "保存 PMF", pmf_path, "All Files (*)")
        if fname:
            shutil.copy(pmf_path, fname)
            self.main_window.log(f"PMF 已保存到 {fname}")

    def _start_worker(self, args, input_text=None, on_finish=None):
        w = self.runner.create_worker(args, cwd=self.ctx.cwd, input_text=input_text)
        w.output_signal.connect(self.main_window.log)
        if on_finish:
            w.finished_signal.connect(on_finish)
        w.start()
