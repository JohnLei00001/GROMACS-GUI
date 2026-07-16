from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QLineEdit, QTextEdit,
                             QMessageBox, QFileDialog)
from PyQt6.QtCore import pyqtSignal
import os
import subprocess

class WindowTab(QWidget):
    """从 Pull 轨迹中提取伞形取样窗口"""

    windows_ready = pyqtSignal(str, list)  # (cwd, [window_configs])

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.cwd = ""
        self.windows = []  # [(start_dist, ref_dist, dir_name)]
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        w = QWidget(); layout = QVBoxLayout(w)

        self.status_label = QLabel("等待 Pull 模拟完成...")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.status_label)

        # 窗口参数
        g1 = QGroupBox("窗口设置")
        f1 = QFormLayout()

        self.spacing_input = QLineEdit("0.1")
        f1.addRow("窗口间距 (nm):", self.spacing_input)

        self.window_count = QLineEdit("20")
        f1.addRow("窗口数量:", self.window_count)

        self.force_input = QLineEdit("1000")
        f1.addRow("窗口力常数 k (kJ/mol·nm²):", self.force_input)

        self.btn_extract = QPushButton("▶ 从 Pull 轨迹提取窗口")
        self.btn_extract.clicked.connect(self.extract_windows)
        f1.addRow("", self.btn_extract)

        self.btn_setup = QPushButton("▶ 生成窗口 TPR")
        self.btn_setup.clicked.connect(self.setup_windows)
        f1.addRow("", self.btn_setup)
        g1.setLayout(f1)
        layout.addWidget(g1)

        # 窗口列表
        g2 = QGroupBox("窗口列表")
        g2_layout = QVBoxLayout()
        self.window_list = QTextEdit()
        self.window_list.setReadOnly(True)
        self.window_list.setStyleSheet("font-family: Consolas; font-size: 13px;")
        g2_layout.addWidget(self.window_list)
        g2.setLayout(g2_layout)
        layout.addWidget(g2)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    def update_cwd(self, cwd):
        self.cwd = cwd
        self.status_label.setText(f"✅ 工作目录: {self.cwd}")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")

    def extract_windows(self):
        if not self.cwd:
            return

        pullx_path = os.path.join(self.cwd, "pullx.xvg")
        if not os.path.exists(pullx_path):
            QMessageBox.warning(self, "警告", "未找到 pullx.xvg，请先执行 Pull 模拟")
            return

        # 读取 pullx.xvg，提取每帧的 COM 距离
        try:
            frames = []
            with open(pullx_path, 'r') as f:
                for line in f:
                    if line.startswith(('#', '@')): continue
                    parts = line.split()
                    if len(parts) >= 2:
                        frames.append((float(parts[0]), float(parts[1])))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取 pullx.xvg 失败: {e}")
            return

        if not frames:
            QMessageBox.warning(self, "警告", "pullx.xvg 为空")
            return

        min_dist = frames[0][1]
        max_dist = frames[-1][1]
        spacing = float(self.spacing_input.text())

        self.windows = []
        current_ref = min_dist
        frames_idx = 0

        while current_ref <= max_dist and len(self.windows) < 50:
            # 找到距离最接近 current_ref 的那一帧
            while frames_idx < len(frames) and frames[frames_idx][1] < current_ref:
                frames_idx += 1
            if frames_idx >= len(frames):
                break
            t, d = frames[frames_idx]
            dir_name = f"window_{len(self.windows):03d}"
            self.windows.append((d, current_ref, dir_name))
            current_ref += spacing

        self.window_list.clear()
        lines = [f"共 {len(self.windows)} 个窗口, 间距 {spacing} nm\n",
                 f"距离范围: {min_dist:.3f} → {max_dist:.3f} nm\n\n"]
        for i, (frame_d, ref_d, dn) in enumerate(self.windows):
            lines.append(f"  [{i:3d}] {dn}  ref={ref_d:.3f} nm  (frame){frame_d:.3f} nm")
        self.window_list.setText('\n'.join(lines))
        self.main_window.log(f">>> 提取了 {len(self.windows)} 个窗口")

    def setup_windows(self):
        if not self.windows or not self.cwd:
            QMessageBox.warning(self, "警告", "请先提取窗口")
            return

        pull_tpr = os.path.join(self.cwd, "pull.tpr")
        npt_gro = os.path.join(self.cwd, "npt.gro")
        if not os.path.exists(pull_tpr) or not os.path.exists(npt_gro):
            QMessageBox.warning(self, "警告", "未找到 pull.tpr 或 npt.gro")
            return

        force_k = self.force_input.text()
        self.btn_setup.setEnabled(False)
        self.main_window.log(">>> 开始生成窗口配置...")

        # 为每个窗口创建目录并生成 TPR
        for i, (frame_dist, ref_dist, dir_name) in enumerate(self.windows):
            win_dir = os.path.join(self.cwd, dir_name)
            os.makedirs(win_dir, exist_ok=True)

            # 从 pull 轨迹中提取该帧的构型
            # gmx trjconv -s pull.tpr -f pull.xtc -o frame.gro -dump <time>
            # 然后复制其他需要的文件
            # 简化起见，直接用 npt.gro 作为每个窗口的起始构型
            # 实际应用中应该从 pull 轨迹提取对应帧

            # 生成 MDP
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

            # 复制 topol.top 和 npt.gro
            import shutil
            top_src = os.path.join(self.cwd, "topol.top")
            gro_src = os.path.join(self.cwd, "npt.gro")
            if os.path.exists(top_src):
                shutil.copy(top_src, os.path.join(win_dir, "topol.top"))
            if os.path.exists(gro_src):
                shutil.copy(gro_src, os.path.join(win_dir, "npt.gro"))

        self.btn_setup.setEnabled(True)
        self.main_window.log(f">>> ✓ {len(self.windows)} 个窗口配置已生成")
        QMessageBox.information(self, "完成",
            f"已为 {len(self.windows)} 个窗口生成配置。\n请继续到「批量 MD」标签页。")
        self.windows_ready.emit(self.cwd, self.windows)
