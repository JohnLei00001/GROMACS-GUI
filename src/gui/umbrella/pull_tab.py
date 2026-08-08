"""Umbrella Pull Tab —— 牵引模拟

Pull 参数是伞形取样的核心配置，不做 MDP 折叠（用户需要能看到每个参数）。
输入/输出路径通过 WorkflowContext 传递，不再硬编码猜测。
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel, QGroupBox,
                             QFormLayout, QComboBox, QLineEdit,
                             QMessageBox)
from PyQt6.QtCore import pyqtSignal
from .workflow_context import UmbrellaContext
import os
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class PullTab(QWidget):
    pull_done = pyqtSignal(UmbrellaContext)

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

        self.status_label = QLabel("等待体系构建完成...")
        self.status_label.setStyleSheet("color: #8a8a8a; font-weight: bold; font-size: 11pt;")
        layout.addWidget(self.status_label)

        g1 = QGroupBox("Pull 模拟参数")
        f1 = QFormLayout()
        self.group1_input = QLineEdit("Protein")
        f1.addRow("组 1 名称:", self.group1_input)
        self.group2_input = QLineEdit("Ligand")
        f1.addRow("组 2 名称:", self.group2_input)
        self.geom_combo = QComboBox()
        self.geom_combo.addItems(["distance", "direction", "direction-periodic", "cylinder"])
        self.geom_combo.setCurrentText("distance")
        f1.addRow("坐标几何:", self.geom_combo)
        self.dir_input = QLineEdit("0 0 1")
        f1.addRow("pull 方向 (dim=Y/N=Z):", self.dir_input)
        self.rate_input = QLineEdit("0.01")
        f1.addRow("拉动速率 (nm/ps):", self.rate_input)
        self.force_input = QLineEdit("1000")
        f1.addRow("力常数 k (kJ/mol·nm²):", self.force_input)
        self.nsteps_input = QLineEdit("500000")
        f1.addRow("步数 (nsteps):", self.nsteps_input)

        self.btn_run = QPushButton("▶ 执行 Pull 模拟")
        self.btn_run.setStyleSheet("QPushButton { padding: 8px 16px; font-weight: bold; }")
        self.btn_run.clicked.connect(self.run_pull)
        f1.addRow("", self.btn_run)
        g1.setLayout(f1)
        layout.addWidget(g1)

        g2 = QGroupBox("质心距离 (Pull COM Distance)")
        g2_layout = QVBoxLayout()
        self.canvas = FigureCanvas(Figure(figsize=(6, 3)))
        self.ax = self.canvas.figure.add_subplot(111)
        self.ax.set_xlabel("Time (ps)")
        self.ax.set_ylabel("Distance (nm)")
        self.ax.grid(True, alpha=0.3)
        self.canvas.figure.tight_layout()
        g2_layout.addWidget(self.canvas)
        g2.setLayout(g2_layout)
        layout.addWidget(g2)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    def update_context(self, ctx: UmbrellaContext):
        self.ctx = ctx
        self.status_label.setText(f"工作目录: {ctx.cwd}  |  输入: {ctx.npt_gro}")
        self.status_label.setStyleSheet("color: #89d185; font-weight: bold; font-size: 11pt;")

    def run_pull(self):
        if not self.ctx:
            QMessageBox.warning(self, "提示", "请先完成 NPT。")
            return

        npt_gro = self.ctx.resolve(self.ctx.npt_gro)
        top_file = self.ctx.resolve(self.ctx.topology_file)
        if not os.path.exists(npt_gro) or not os.path.exists(top_file):
            QMessageBox.warning(self, "提示",
                f"未找到 npt.gro / topol.top，请先完成 NPT")
            return

        g1 = self.group1_input.text()
        g2 = self.group2_input.text()
        rate = self.rate_input.text()
        force_k = self.force_input.text()
        nsteps = self.nsteps_input.text()
        geometry = self.geom_combo.currentText()
        direction = self.dir_input.text()

        mdp_path = self.ctx.resolve("pull.mdp")
        with open(mdp_path, "w") as f:
            f.write("; Pull simulation MDP\n")
            f.write("integrator = md\ndt = 0.002\nnsteps = {}\n".format(nsteps))
            f.write("nstxout = 5000\nnstvout = 5000\nnstenergy = 5000\nnstlog = 5000\n")
            f.write("nstxout-compressed = 5000\ncompressed-x-grps = System\n")
            f.write("tcoupl = V-rescale\ntc-grps = System\ntau-t = 0.1\nref-t = 300\n")
            f.write("pcoupl = Parrinello-Rahman\npcoupltype = isotropic\ntau-p = 2.0\n")
            f.write("ref-p = 1.0\ncompressibility = 4.5e-5\n")
            f.write("pbc = xyz\ncutoff-scheme = Verlet\nns_type = grid\n")
            f.write("coulombtype = PME\nrcoulomb = 1.0\nrvdw = 1.0\nDispCorr = EnerPres\n")
            f.write("constraints = h-bonds\nconstraint-algorithm = LINCS\n")
            f.write("continuation = yes\ngen-vel = no\n\n")
            f.write("; Pull code\n")
            f.write("pull = yes\n")
            f.write("pull-ngroups = 2\n")
            f.write("pull-group1-name = {}\n".format(g1))
            f.write("pull-group2-name = {}\n".format(g2))
            f.write("pull-ncoords = 1\n")
            f.write("pull-coord1-type = umbrella\n")
            f.write("pull-coord1-geometry = {}\n".format(geometry))
            f.write("pull-coord1-groups = 1 2\n")
            f.write("pull-coord1-rate = {}\n".format(rate))
            f.write("pull-coord1-k = {}\n".format(force_k))
            f.write("pull-coord1-start = yes\n")
            if geometry == "direction":
                f.write("pull-coord1-vec = {}\n".format(direction))

        self.btn_run.setEnabled(False)
        self.status_label.setText("Pull 运行中...")
        self.status_label.setStyleSheet("color: #d7ba7d; font-weight: bold; font-size: 11pt;")

        a1 = ["grompp", "-f", "pull.mdp", "-c", self.ctx.npt_gro, "-r", self.ctx.npt_gro,
              "-p", self.ctx.topology_file, "-o", "pull.tpr", "-maxwarn", "2"]
        self._start_worker(a1, on_finish=lambda s, m: self._on_grompp_done(s, m))

    def _on_grompp_done(self, success, message):
        if not success:
            self.btn_run.setEnabled(True)
            self.status_label.setText("Pull grompp 失败")
            self.status_label.setStyleSheet("color: #f48771; font-weight: bold; font-size: 11pt;")
            QMessageBox.critical(self, "错误", f"Pull grompp 失败:\n{message}")
            return
        self.main_window.log(">>> 开始 Pull 模拟...")
        self._start_worker(["mdrun", "-deffnm", "pull", "-v"],
                           on_finish=lambda s, m: self._on_pull_done(s, m))

    def _on_pull_done(self, success, message):
        self.btn_run.setEnabled(True)
        if not success:
            self.status_label.setText("Pull 失败")
            self.status_label.setStyleSheet("color: #f48771; font-weight: bold; font-size: 11pt;")
            QMessageBox.critical(self, "错误", f"Pull 模拟失败:\n{message}")
            return
        self.main_window.log(">>> Pull 模拟完成")
        self.status_label.setText("Pull 完成")
        self.status_label.setStyleSheet("color: #89d185; font-weight: bold; font-size: 11pt;")
        self._plot_pullx()
        QMessageBox.information(self, "完成",
            "Pull 模拟完成！已生成 pullx.xvg 和 pullf.xvg。\n请继续到「窗口设置」。")
        self.pull_done.emit(self.ctx)

    def _plot_pullx(self):
        pullx_path = self.ctx.resolve("pullx.xvg")
        if not os.path.exists(pullx_path):
            return
        try:
            times, dists = [], []
            with open(pullx_path) as f:
                for line in f:
                    if line.startswith(('#', '@')): continue
                    parts = line.split()
                    if len(parts) >= 2:
                        times.append(float(parts[0]))
                        dists.append(float(parts[1]))
            if times:
                self.ax.clear()
                self.ax.plot(times, dists, 'b-', linewidth=0.8)
                self.ax.set_xlabel("Time (ps)")
                self.ax.set_ylabel("COM Distance (nm)")
                self.ax.grid(True, alpha=0.3)
                self.canvas.figure.tight_layout()
                self.canvas.draw()
        except Exception as e:
            self.main_window.log(f"绘图失败: {e}")

    def _start_worker(self, args, input_text=None, on_finish=None):
        w = self.runner.create_worker(args, cwd=self.ctx.cwd, input_text=input_text)
        w.output_signal.connect(self.main_window.log)
        if on_finish:
            w.finished_signal.connect(on_finish)
        w.start()
