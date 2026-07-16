from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QComboBox, QLineEdit, 
                             QMessageBox, QCheckBox, QProgressBar, QFileDialog)
from PyQt6.QtCore import pyqtSignal
import os
import re
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

class PullTab(QWidget):
    """Pull 模拟：配置参数 → 执行拉动 → 预览 COM 距离"""
    
    pull_done = pyqtSignal(str)  # (cwd)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.cwd = ""
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        w = QWidget(); layout = QVBoxLayout(w)

        # 状态
        self.status_label = QLabel("等待体系构建完成... (请先完成「1. 体系构建」)")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.status_label)

        # Pull 参数
        g1 = QGroupBox("Pull 模拟参数")
        f1 = QFormLayout()

        # 组 1 名称
        self.group1_input = QLineEdit("Protein")
        f1.addRow("组 1 名称:", self.group1_input)

        # 组 2 名称
        self.group2_input = QLineEdit("Ligand")
        f1.addRow("组 2 名称:", self.group2_input)

        # 反应坐标几何
        self.geom_combo = QComboBox()
        self.geom_combo.addItems(["distance", "direction", "direction-periodic", "cylinder"])
        self.geom_combo.setCurrentText("distance")
        f1.addRow("坐标几何:", self.geom_combo)

        # 方向 (仅 direction 类型使用)
        self.dir_input = QLineEdit("0 0 1")
        f1.addRow("pull 方向 (dim=Y/N=Z):", self.dir_input)

        # 拉动速率 (nm/ps)
        self.rate_input = QLineEdit("0.01")
        f1.addRow("拉动速率 (nm/ps):", self.rate_input)

        # 力常数 (kJ/mol·nm²)
        self.force_input = QLineEdit("1000")
        f1.addRow("力常数 k (kJ/mol·nm²):", self.force_input)

        # 步数
        self.nsteps_input = QLineEdit("500000")
        f1.addRow("步数 (nsteps):", self.nsteps_input)

        self.btn_run = QPushButton("▶ 执行 Pull 模拟")
        self.btn_run.clicked.connect(self.run_pull)
        f1.addRow("", self.btn_run)
        g1.setLayout(f1)
        layout.addWidget(g1)

        # COM 距离实时图
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

    def update_cwd(self, cwd):
        self.cwd = cwd
        self.status_label.setText(f"✅ 工作目录: {self.cwd}")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")

    def run_pull(self):
        if not self.cwd:
            QMessageBox.warning(self, "警告", "请先完成体系构建")
            return

        npt_gro = os.path.join(self.cwd, "npt.gro")
        top_file = os.path.join(self.cwd, "topol.top")
        if not os.path.exists(npt_gro) or not os.path.exists(top_file):
            QMessageBox.warning(self, "警告", "未找到 npt.gro / topol.top，请先完成体系构建")
            return

        # 生成 pull MDP
        g1 = self.group1_input.text()
        g2 = self.group2_input.text()
        rate = self.rate_input.text()
        force_k = self.force_input.text()
        nsteps = self.nsteps_input.text()
        geometry = self.geom_combo.currentText()
        direction = self.dir_input.text()

        mdp_path = os.path.join(self.cwd, "pull.mdp")
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
        a1 = ["grompp", "-f", "pull.mdp", "-c", "npt.gro", "-r", "npt.gro",
              "-p", "topol.top", "-o", "pull.tpr", "-maxwarn", "2"]
        self._start_worker(a1, on_finish=lambda s, m: self._on_grompp_done(s, m))

    def _on_grompp_done(self, success, message):
        if not success:
            self.btn_run.setEnabled(True)
            QMessageBox.critical(self, "错误", f"Pull grompp 失败:\n{message}")
            return
        self.main_window.log(">>> 开始 Pull 模拟...")
        self._start_worker(["mdrun", "-deffnm", "pull", "-v"],
                           on_finish=lambda s, m: self._on_pull_done(s, m))

    def _on_pull_done(self, success, message):
        self.btn_run.setEnabled(True)
        if not success:
            QMessageBox.critical(self, "错误", f"Pull 模拟失败:\n{message}")
            return
        self.main_window.log(">>> ✓ Pull 模拟完成")
        self._plot_pullx()
        QMessageBox.information(self, "完成",
            "Pull 模拟完成！\n已生成 pullx.xvg（COM 距离）和 pullf.xvg（力）。\n请继续到「窗口设置」标签页。")
        self.pull_done.emit(self.cwd)

    def _plot_pullx(self):
        """读取 pullx.xvg 并绘图"""
        pullx_path = os.path.join(self.cwd, "pullx.xvg")
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
        w = self.runner.create_worker(args, cwd=self.cwd, input_text=input_text)
        w.output_signal.connect(self.main_window.log)
        if on_finish:
            w.finished_signal.connect(on_finish)
        w.start()
