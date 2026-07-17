from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel, QGroupBox, QFormLayout,
                             QComboBox, QTextEdit, QMessageBox, QDialog)
from PyQt6.QtCore import pyqtSignal
from gui.mdp_editor import MDPEditor
import os

class NptTab(QWidget):
    npt_done = pyqtSignal(str)

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

        self.status = QLabel("等待 NVT 完成...")
        self.status.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.status)

        # 1. MDP
        mdp_group = QGroupBox("1. 准备 NPT 参数 (npt.mdp)")
        mdp_l = QVBoxLayout()
        self.mdp_content = QTextEdit()
        self.mdp_content.setText(
            "title                   = NPT equilibration\n"
            "; Run parameters\n"
            "integrator              = md        ; leap-frog integrator\n"
            "nsteps                  = 50000     ; 2 * 50000 = 100 ps\n"
            "dt                      = 0.002     ; 2 fs\n"
            "; Output control\n"
            "nstxout                 = 500       ; save coordinates every 1.0 ps\n"
            "nstvout                 = 500       ; save velocities every 1.0 ps\n"
            "nstenergy               = 500       ; save energies every 1.0 ps\n"
            "nstlog                  = 500       ; update log file every 1.0 ps\n"
            "; Bond parameters\n"
            "continuation            = yes       ; Restarting after NVT\n"
            "constraint_algorithm    = lincs     ; holonomic constraints\n"
            "constraints             = h-bonds   ; bonds involving H are constrained\n"
            "lincs_iter              = 1         ; accuracy of LINCS\n"
            "lincs_order             = 4         ; also related to accuracy\n"
            "; Nonbonded settings\n"
            "cutoff-scheme           = Verlet    ; Buffered neighbor searching\n"
            "ns_type                 = grid      ; search neighboring grid cells\n"
            "nstlist                 = 10        ; 20 fs, largely irrelevant with Verlet\n"
            "rcoulomb                = 1.0       ; short-range electrostatic cutoff (in nm)\n"
            "rvdw                    = 1.0       ; short-range van der Waals cutoff (in nm)\n"
            "DispCorr                = EnerPres  ; account for cut-off vdW scheme\n"
            "; Electrostatics\n"
            "coulombtype             = PME       ; Particle Mesh Ewald for long-range electrostatics\n"
            "pme_order               = 4         ; cubic interpolation\n"
            "fourierspacing          = 0.16      ; grid spacing for FFT\n"
            "; Temperature coupling\n"
            "tcoupl                  = V-rescale             ; modified Berendsen thermostat\n"
            "tc-grps                 = System                ; coupling group\n"
            "tau_t                   = 0.1                   ; time constant, in ps\n"
            "ref_t                   = 300                   ; reference temperature, in K\n"
            "; Pressure coupling\n"
            "pcoupl                  = Parrinello-Rahman     ; Pressure coupling on in NPT\n"
            "pcoupltype              = isotropic             ; uniform scaling of box vectors\n"
            "tau_p                   = 2.0                   ; time constant, in ps\n"
            "ref_p                   = 1.0                   ; reference pressure, in bar\n"
            "compressibility         = 4.5e-5                ; isothermal compressibility of water, bar^-1\n"
            "refcoord_scaling        = com\n"
            "; Periodic boundary conditions\n"
            "pbc                     = xyz       ; 3-D PBC\n"
            "; Velocity generation\n"
            "gen_vel                 = no        ; Velocity generation is off\n"
        )
        self.mdp_content.setStyleSheet("font-family: Consolas; font-size: 9pt;")
        btn_row = QHBoxLayout()
        btn_edit = QPushButton("打开参数编辑器")
        btn_edit.clicked.connect(self._open_editor)
        btn_save = QPushButton("保存为 npt.mdp")
        btn_save.clicked.connect(self._save_mdp)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_save)
        mdp_l.addWidget(self.mdp_content)
        mdp_l.addLayout(btn_row)
        mdp_group.setLayout(mdp_l)
        layout.addWidget(mdp_group)

        # 2. grompp
        grompp_group = QGroupBox("2. 生成运行文件 (grompp)")
        grompp_l = QFormLayout()
        self.btn_grompp = QPushButton("运行 grompp")
        self.btn_grompp.clicked.connect(self._run_grompp)
        grompp_l.addRow("执行预处理:", self.btn_grompp)
        grompp_group.setLayout(grompp_l)
        layout.addWidget(grompp_group)

        # 3. mdrun
        mdrun_group = QGroupBox("3. 执行 NPT 平衡 (mdrun)")
        mdrun_l = QFormLayout()
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems(["自动检测", "强制使用 GPU", "仅使用 CPU"])
        mdrun_l.addRow("硬件加速:", self.gpu_combo)
        self.btn_mdrun = QPushButton("运行 mdrun")
        self.btn_mdrun.clicked.connect(self._run_mdrun)
        mdrun_l.addRow("执行计算:", self.btn_mdrun)
        mdrun_group.setLayout(mdrun_l)
        layout.addWidget(mdrun_group)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    def update_cwd(self, cwd):
        self.cwd = cwd
        self.status.setText(f"✅ 工作目录: {cwd}")
        self.status.setStyleSheet("color: green; font-weight: bold;")

    def _open_editor(self):
        dlg = MDPEditor(self, "npt", self.mdp_content.toPlainText())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.mdp_content.setText(dlg.get_mdp_content())

    def _save_mdp(self):
        if not self.cwd:
            QMessageBox.warning(self, "警告", "请先完成 NVT")
            return
        try:
            with open(os.path.join(self.cwd, "npt.mdp"), "w") as f:
                f.write(self.mdp_content.toPlainText())
            self.main_window.log("已保存 npt.mdp")
            QMessageBox.information(self, "成功", "npt.mdp 已保存。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def _run_grompp(self):
        if not self.cwd: return
        for f in ["npt.mdp", "nvt.gro", "topol.top"]:
            if not os.path.exists(os.path.join(self.cwd, f)):
                QMessageBox.warning(self, "警告", f"缺少 {f}，请先完成 NVT"); return
        self._set_btns(False)
        args = ["grompp", "-f", "npt.mdp", "-c", "nvt.gro", "-r", "nvt.gro",
                "-p", "topol.top", "-o", "npt.tpr", "-maxwarn", "1"]
        # 如果有 checkpoint 文件，加上 -t 续跑
        if os.path.exists(os.path.join(self.cwd, "nvt.cpt")):
            args.insert(4, "nvt.cpt"); args.insert(4, "-t")
        self._go(args, on_finish=lambda s, m: self._on_grompp_done(s, m))

    def _on_grompp_done(self, success, message):
        self._set_btns(True)
        if success:
            QMessageBox.information(self, "成功", "grompp 完成！已生成 npt.tpr")
        else:
            QMessageBox.critical(self, "错误", f"grompp (NPT) 失败: {message}")

    def _run_mdrun(self):
        if not self.cwd: return
        if not os.path.exists(os.path.join(self.cwd, "npt.tpr")):
            QMessageBox.warning(self, "警告", "未找到 npt.tpr，请先运行 grompp"); return
        args = ["mdrun", "-v", "-deffnm", "npt"]
        gpu = self.gpu_combo.currentText()
        if gpu == "强制使用 GPU": args.extend(["-nb", "gpu"])
        elif gpu == "仅使用 CPU": args.extend(["-nb", "cpu"])
        self._set_btns(False)
        self._go(args, on_finish=lambda s, m: self._on_mdrun_done(s, m))

    def _on_mdrun_done(self, success, message):
        self._set_btns(True)
        if success:
            self.main_window.log(">>> ✓ NPT 完成")
            QMessageBox.information(self, "成功", "NPT 平衡完成！")
            self.npt_done.emit(self.cwd)
        else:
            QMessageBox.critical(self, "错误", f"mdrun (NPT) 失败: {message}")

    def _set_btns(self, enabled):
        for b in self.findChildren(QPushButton): b.setEnabled(enabled)

    def _go(self, args, input_text=None, on_finish=None):
        w = self.runner.create_worker(args, cwd=self.cwd, input_text=input_text)
        w.output_signal.connect(self.main_window.log)
        if on_finish: w.finished_signal.connect(on_finish)
        w.start()
