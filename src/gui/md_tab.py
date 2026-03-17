from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QComboBox, QLineEdit, 
                             QTextEdit, QMessageBox, QDialog)
import os
from .mdp_editor import MDPEditor

class MDTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. MD MDP
        mdp_group = QGroupBox("1. 准备生产模拟参数 (md.mdp)")
        mdp_layout = QVBoxLayout()
        
        self.md_mdp_content = QTextEdit()
        default_md_mdp = (
            "title                   = OPLS Lysozyme MD simulation \n"
            "; Run parameters\n"
            "integrator              = md        ; leap-frog integrator\n"
            "nsteps                  = 500000    ; 2 * 500000 = 1000 ps (1 ns)\n"
            "dt                      = 0.002     ; 2 fs\n"
            "; Output control\n"
            "nstxout                 = 0         ; suppress bulky .trr file by specifying \n"
            "nstvout                 = 0         ; 0 for output frequency of nstxout,\n"
            "nstfout                 = 0         ; nstvout, and nstfout\n"
            "nstenergy               = 5000      ; save energies every 10.0 ps\n"
            "nstlog                  = 5000      ; update log file every 10.0 ps\n"
            "nstxout-compressed      = 5000      ; save compressed coordinates every 10.0 ps\n"
            "compressed-x-grps       = System    ; save the whole system\n"
            "; Bond parameters\n"
            "continuation            = yes       ; Restarting after NPT \n"
            "constraint_algorithm    = lincs     ; holonomic constraints \n"
            "constraints             = h-bonds   ; bonds involving H are constrained\n"
            "lincs_iter              = 1         ; accuracy of LINCS\n"
            "lincs_order             = 4         ; also related to accuracy\n"
            "; Nonbonded settings \n"
            "cutoff-scheme           = Verlet    ; Buffered neighbor searching\n"
            "ns_type                 = grid      ; search neighboring grid cells\n"
            "nstlist                 = 10        ; 20 fs, largely irrelevant with Verlet scheme\n"
            "rcoulomb                = 1.0       ; short-range electrostatic cutoff (in nm)\n"
            "rvdw                    = 1.0       ; short-range van der Waals cutoff (in nm)\n"
            "; Electrostatics\n"
            "coulombtype             = PME       ; Particle Mesh Ewald for long-range electrostatics\n"
            "pme_order               = 4         ; cubic interpolation\n"
            "fourierspacing          = 0.16      ; grid spacing for FFT\n"
            "; Temperature coupling is on\n"
            "tcoupl                  = V-rescale             ; modified Berendsen thermostat\n"
            "tc-grps                 = Protein Non-Protein   ; two coupling groups - more accurate\n"
            "tau_t                   = 0.1     0.1           ; time constant, in ps\n"
            "ref_t                   = 300     300           ; reference temperature, one for each group, in K\n"
            "; Pressure coupling is on\n"
            "pcoupl                  = Parrinello-Rahman     ; Pressure coupling on in NPT\n"
            "pcoupltype              = isotropic             ; uniform scaling of box vectors\n"
            "tau_p                   = 2.0                   ; time constant, in ps\n"
            "ref_p                   = 1.0                   ; reference pressure, in bar\n"
            "compressibility         = 4.5e-5                ; isothermal compressibility of water, bar^-1\n"
            "; Periodic boundary conditions\n"
            "pbc                     = xyz       ; 3-D PBC\n"
            "; Dispersion correction\n"
            "DispCorr                = EnerPres  ; account for cut-off vdW scheme\n"
            "; Velocity generation\n"
            "gen_vel                 = no        ; Velocity generation is off \n"
        )
        self.md_mdp_content.setText(default_md_mdp)
        self.md_mdp_content.setStyleSheet("font-family: Consolas; font-size: 9pt;")
        
        btn_layout = QHBoxLayout()
        btn_edit_md = QPushButton("打开参数编辑器")
        btn_edit_md.clicked.connect(self.open_editor)
        
        btn_save_md_mdp = QPushButton("保存为 md.mdp")
        btn_save_md_mdp.clicked.connect(lambda: self.save_mdp("md.mdp", self.md_mdp_content.toPlainText()))
        
        btn_layout.addWidget(btn_edit_md)
        btn_layout.addWidget(btn_save_md_mdp)
        
        mdp_layout.addWidget(self.md_mdp_content)
        mdp_layout.addLayout(btn_layout)
        mdp_group.setLayout(mdp_layout)
        layout.addWidget(mdp_group)

        # 2. 运行 MD
        run_group = QGroupBox("2. 运行生产模拟 (Production MD)")
        run_layout = QFormLayout()
        
        btn_grompp_md = QPushButton("1. grompp (生成 md_0_1.tpr)")
        btn_grompp_md.clicked.connect(self.run_grompp_md)
        
        self.md_gpu_combo = QComboBox()
        self.md_gpu_combo.addItems(["自动检测", "强制使用 GPU", "仅使用 CPU"])
        
        btn_mdrun_md = QPushButton("2. mdrun (执行生产模拟)")
        btn_mdrun_md.clicked.connect(self.run_mdrun_md)
        
        run_layout.addRow("预处理:", btn_grompp_md)
        run_layout.addRow("硬件加速:", self.md_gpu_combo)
        run_layout.addRow("执行计算:", btn_mdrun_md)
        
        run_group.setLayout(run_layout)
        layout.addWidget(run_group)
        
    def open_editor(self):
        current_content = self.md_mdp_content.toPlainText()
        dialog = MDPEditor(self, "md", current_content)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_content = dialog.get_mdp_content()
            self.md_mdp_content.setText(new_content)

    def get_cwd(self):
        try:
            topo_tab = self.main_window.solution_tabs.widget(0)
            return topo_tab.cwd
        except:
            return None

    def save_mdp(self, filename, content):
        cwd = self.get_cwd()
        if not cwd:
            QMessageBox.warning(self, "警告", "请先在'拓扑与水箱'步骤中确定工作目录！")
            return
            
        mdp_path = os.path.join(cwd, filename)
        try:
            with open(mdp_path, "w") as f:
                f.write(content)
            self.main_window.log(f"已成功保存 {filename} 文件: {mdp_path}")
            QMessageBox.information(self, "成功", f"{filename} 已保存。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存 {filename} 文件失败: {str(e)}")

    def run_grompp_md(self):
        cwd = self.get_cwd()
        if not cwd: return
            
        required_files = ["md.mdp", "npt.gro", "topol.top", "npt.cpt"]
        for f in required_files:
            if not os.path.exists(os.path.join(cwd, f)):
                QMessageBox.warning(self, "警告", f"缺少必要文件: {f}\n请确保已完成 NPT 平衡步骤。")
                return

        args = ["grompp", "-f", "md.mdp", "-c", "npt.gro", "-t", "npt.cpt", "-p", "topol.top", "-o", "md_0_1.tpr", "-maxwarn", "1"]
        
        self.main_window.log(f"\n>>> 正在运行: gmx {' '.join(args)}")
        
        self.worker_md_grompp = self.runner.create_worker(args, cwd=cwd)
        self.worker_md_grompp.output_signal.connect(self.main_window.log)
        self.worker_md_grompp.finished_signal.connect(self.on_md_grompp_finished)
        
        self.set_buttons_enabled(False)
        self.worker_md_grompp.start()

    def on_md_grompp_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "成功", "grompp 运行完成！生成了 md_0_1.tpr")
        else:
            QMessageBox.critical(self, "错误", f"grompp (MD) 运行失败: {message}")

    def run_mdrun_md(self):
        cwd = self.get_cwd()
        if not cwd: return
            
        if not os.path.exists(os.path.join(cwd, "md_0_1.tpr")):
            QMessageBox.warning(self, "警告", "未找到 md_0_1.tpr，请先运行 MD grompp！")
            return

        args = ["mdrun", "-v", "-deffnm", "md_0_1"]
        gpu_opt = self.md_gpu_combo.currentText()
        if gpu_opt == "强制使用 GPU": args.extend(["-nb", "gpu"])
        elif gpu_opt == "仅使用 CPU": args.extend(["-nb", "cpu"])

        self.main_window.log(f"\n>>> 正在运行: gmx {' '.join(args)}")
        
        self.worker_md_mdrun = self.runner.create_worker(args, cwd=cwd)
        self.worker_md_mdrun.output_signal.connect(self.main_window.log)
        self.worker_md_mdrun.finished_signal.connect(self.on_md_mdrun_finished)
        
        self.set_buttons_enabled(False)
        self.worker_md_mdrun.start()

    def on_md_mdrun_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "成功", "生产模拟完成！生成了 md_0_1.xtc/trr/gro 等文件。")
        else:
            QMessageBox.critical(self, "错误", f"mdrun (MD) 运行失败: {message}")

    def set_buttons_enabled(self, enabled):
        for child in self.findChildren(QPushButton):
            child.setEnabled(enabled)
