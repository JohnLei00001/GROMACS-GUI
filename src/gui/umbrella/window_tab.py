"""Umbrella Window Tab —— 从 Pull 轨迹提取伞形取样窗口"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel,
                             QFormLayout, QLineEdit, QTextEdit,
                             QMessageBox)
from PyQt6.QtCore import pyqtSignal
from gui.i18n import tr, trf
from gui.theme import set_role
from gui.widgets import StepCard
from .workflow_context import UmbrellaContext
import os, shutil


class WindowTab(QWidget):
    windows_ready = pyqtSignal(UmbrellaContext)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.ctx: UmbrellaContext = None
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        w = QWidget(); layout = QVBoxLayout(w); layout.setSpacing(10)

        self.status_label = QLabel(tr("等待 Pull 模拟完成..."))
        set_role(self.status_label, "muted")
        layout.addWidget(self.status_label)

        g1_card = StepCard("", tr("窗口设置"))
        f1 = g1_card.content_layout
        self.spacing_input = QLineEdit("0.1")
        f1.addRow(tr("窗口间距 (nm):"), self.spacing_input)
        self.window_count = QLineEdit("20")
        f1.addRow(tr("窗口数量:"), self.window_count)
        self.force_input = QLineEdit("1000")
        f1.addRow(tr("窗口力常数 k (kJ/mol·nm²):"), self.force_input)

        self.btn_extract = QPushButton(tr("▶ 从 Pull 轨迹提取窗口"))
        self.btn_extract.clicked.connect(self.extract_windows)
        set_role(self.btn_extract, "primary")
        f1.addRow("", self.btn_extract)
        self.btn_setup = QPushButton(tr("▶ 生成窗口 TPR"))
        self.btn_setup.clicked.connect(self.setup_windows)
        set_role(self.btn_setup, "primary")
        f1.addRow("", self.btn_setup)
        layout.addWidget(g1_card)

        g2_card = StepCard("", tr("窗口列表"), layout_kind="vbox")
        g2_layout = g2_card.content_layout
        self.window_list = QTextEdit()
        self.window_list.setReadOnly(True)
        self.window_list.setStyleSheet("font-family: Consolas; font-size: 13px;")
        g2_layout.addWidget(self.window_list)
        layout.addWidget(g2_card)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    def update_context(self, ctx: UmbrellaContext):
        self.ctx = ctx
        self.status_label.setText(trf("工作目录: {cwd}", cwd=ctx.cwd))
        set_role(self.status_label, "ok")

    def extract_windows(self):
        if not self.ctx:
            return
        pullx_path = self.ctx.resolve("pullx.xvg")
        if not os.path.exists(pullx_path):
            QMessageBox.warning(self, tr("警告"), tr("未找到 pullx.xvg，请先执行 Pull 模拟"))
            return
        try:
            frames = []
            with open(pullx_path, 'r') as f:
                for line in f:
                    if line.startswith(('#', '@')): continue
                    parts = line.split()
                    if len(parts) >= 2:
                        frames.append((float(parts[0]), float(parts[1])))
        except Exception as e:
            QMessageBox.critical(self, tr("错误"), trf("读取 pullx.xvg 失败: {err}", err=e))
            return
        if not frames:
            QMessageBox.warning(self, tr("警告"), tr("pullx.xvg 为空"))
            return

        min_dist = frames[0][1]; max_dist = frames[-1][1]
        spacing = float(self.spacing_input.text())

        self.ctx.windows = []
        current_ref = min_dist; frames_idx = 0
        while current_ref <= max_dist and len(self.ctx.windows) < 50:
            while frames_idx < len(frames) and frames[frames_idx][1] < current_ref:
                frames_idx += 1
            if frames_idx >= len(frames): break
            t, d = frames[frames_idx]
            dir_name = f"window_{len(self.ctx.windows):03d}"
            self.ctx.windows.append((d, current_ref, dir_name))
            current_ref += spacing

        lines = [trf("共 {n} 个窗口, 间距 {spacing} nm", n=len(self.ctx.windows), spacing=spacing) + "\n",
                 trf("距离范围: {min} → {max} nm", min=f"{min_dist:.3f}", max=f"{max_dist:.3f}") + "\n\n"]
        for i, (frame_d, ref_d, dn) in enumerate(self.ctx.windows):
            lines.append(f"  [{i:3d}] {dn}  ref={ref_d:.3f} nm  (frame){frame_d:.3f} nm")
        self.window_list.setText('\n'.join(lines))
        self.main_window.log(trf(">>> 提取了 {n} 个窗口", n=len(self.ctx.windows)))

    def setup_windows(self):
        if not self.ctx or not self.ctx.windows:
            QMessageBox.warning(self, tr("警告"), tr("请先提取窗口"))
            return
        pull_tpr = self.ctx.resolve("pull.tpr")
        npt_gro = self.ctx.resolve("npt.gro")
        if not os.path.exists(pull_tpr) or not os.path.exists(npt_gro):
            QMessageBox.warning(self, tr("警告"), tr("未找到 pull.tpr 或 npt.gro"))
            return

        force_k = self.force_input.text()
        self.btn_setup.setEnabled(False)
        self.main_window.log(tr(">>> 开始生成窗口配置..."))

        for i, (frame_dist, ref_dist, dir_name) in enumerate(self.ctx.windows):
            win_dir = os.path.join(self.ctx.cwd, dir_name)
            os.makedirs(win_dir, exist_ok=True)

            mdp_path = os.path.join(win_dir, "umbrella.mdp")
            with open(mdp_path, "w") as f:
                f.write("; Umbrella sampling window MDP\n")
                f.write("integrator = md\ndt = 0.002\nnsteps = 250000\n")
                f.write("nstxout = 5000\nnstvout = 5000\nnstenergy = 5000\nnstlog = 5000\n")
                f.write("tcoupl = V-rescale\ntc-grps = System\ntau-t = 0.1\nref-t = 300\n")
                f.write("pcoupl = Parrinello-Rahman\npcoupltype = isotropic\ntau-p = 2.0\n")
                f.write("ref-p = 1.0\ncompressibility = 4.5e-5\n")
                f.write("pbc = xyz\ncutoff-scheme = Verlet\nns_type = grid\n")
                f.write("coulombtype = PME\nrcoulomb = 1.0\nrvdw = 1.0\nDispCorr = EnerPres\n")
                f.write("constraints = h-bonds\nconstraint-algorithm = LINCS\n")
                f.write("continuation = yes\ngen-vel = yes\ngen-temp = 300\ngen-seed = -1\n\n")
                f.write("; Umbrella restraint\n")
                f.write("pull = yes\n")
                f.write("pull-ngroups = 2\n")
                f.write("pull-group1-name = Protein\n")
                f.write("pull-group2-name = Ligand\n")
                f.write("pull-ncoords = 1\n")
                f.write("pull-coord1-type = umbrella\n")
                f.write("pull-coord1-geometry = distance\n")
                f.write("pull-coord1-groups = 1 2\n")
                f.write("pull-coord1-k = {}\n".format(force_k))
                f.write("pull-coord1-rate = 0.0\n")
                f.write("pull-coord1-init = {:.4f}\n".format(ref_dist))
                f.write("pull-coord1-start = yes\n")

            top_src = self.ctx.resolve("topol.top")
            gro_src = self.ctx.resolve("npt.gro")
            if os.path.exists(top_src):
                shutil.copy(top_src, os.path.join(win_dir, "topol.top"))
            if os.path.exists(gro_src):
                shutil.copy(gro_src, os.path.join(win_dir, "npt.gro"))

        self.btn_setup.setEnabled(True)
        self.main_window.log(trf(">>> ✓ {n} 个窗口配置已生成", n=len(self.ctx.windows)))
        QMessageBox.information(self, tr("完成"),
            trf("已为 {n} 个窗口生成配置。\n请继续到「批量 MD」。", n=len(self.ctx.windows)))
        self.windows_ready.emit(self.ctx)
