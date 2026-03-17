from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QComboBox, QLineEdit, 
                             QTextEdit, QMessageBox, QTabWidget, QDialog)
import os
from .mdp_editor import MDPEditor

class EQTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # 使用子标签页来分隔 NVT 和 NPT
        self.eq_tabs = QTabWidget()
        main_layout.addWidget(self.eq_tabs)
        
        # === NVT 平衡标签页 ===
        self.nvt_tab = QWidget()
        self.init_nvt_tab()
        self.eq_tabs.addTab(self.nvt_tab, "NVT 平衡 (恒温)")
        
        # === NPT 平衡标签页 ===
        self.npt_tab = QWidget()
        self.init_npt_tab()
        self.eq_tabs.addTab(self.npt_tab, "NPT 平衡 (恒压)")
        
    def init_nvt_tab(self):
        layout = QVBoxLayout(self.nvt_tab)
        
        # 1. NVT MDP
        mdp_group = QGroupBox("1. 准备 NVT 参数 (nvt.mdp)")
        mdp_layout = QVBoxLayout()
        
        self.nvt_mdp_content = QTextEdit()
        default_nvt_mdp = (
            "title                   = OPLS Lysozyme NVT equilibration \n"
            "define                  = -DPOSRES  ; position restrain the protein\n"
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
            "continuation            = no        ; first dynamics run\n"
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
            "DispCorr                = EnerPres  ; account for cut-off vdW scheme\n"
            "; Electrostatics\n"
            "coulombtype             = PME       ; Particle Mesh Ewald for long-range electrostatics\n"
            "pme_order               = 4         ; cubic interpolation\n"
            "fourierspacing          = 0.16      ; grid spacing for FFT\n"
            "; Temperature coupling is on\n"
            "tcoupl                  = V-rescale             ; modified Berendsen thermostat\n"
            "tc-grps                 = Protein Non-Protein   ; two coupling groups - more accurate\n"
            "tau_t                   = 0.1     0.1           ; time constant, in ps\n"
            "ref_t                   = 300     300           ; reference temperature, one for each group, in K\n"
            "; Pressure coupling is off\n"
            "pcoupl                  = no        ; no pressure coupling in NVT\n"
            "; Periodic boundary conditions\n"
            "pbc                     = xyz       ; 3-D PBC\n"
            "; Velocity generation\n"
            "gen_vel                 = yes       ; assign velocities from Maxwell distribution\n"
            "gen_temp                = 300       ; temperature for Maxwell distribution\n"
            "gen_seed                = -1        ; generate a random seed\n"
        )
        self.nvt_mdp_content.setText(default_nvt_mdp)
        self.nvt_mdp_content.setStyleSheet("font-family: Consolas; font-size: 9pt;")
        
        btn_layout = QHBoxLayout()
        btn_edit_nvt = QPushButton("打开参数编辑器")
        btn_edit_nvt.clicked.connect(lambda: self.open_editor("nvt"))
        
        btn_save_nvt_mdp = QPushButton("保存为 nvt.mdp")
        btn_save_nvt_mdp.clicked.connect(lambda: self.save_mdp("nvt.mdp", self.nvt_mdp_content.toPlainText()))
        
        btn_layout.addWidget(btn_edit_nvt)
        btn_layout.addWidget(btn_save_nvt_mdp)
        
        mdp_layout.addWidget(self.nvt_mdp_content)
        mdp_layout.addLayout(btn_layout)
        mdp_group.setLayout(mdp_layout)
        layout.addWidget(mdp_group)

        # 2. 运行 NVT
        run_group = QGroupBox("2. 运行 NVT 平衡")
        run_layout = QFormLayout()
        
        btn_grompp_nvt = QPushButton("1. grompp (生成 nvt.tpr)")
        btn_grompp_nvt.clicked.connect(self.run_grompp_nvt)
        
        self.nvt_gpu_combo = QComboBox()
        self.nvt_gpu_combo.addItems(["自动检测", "强制使用 GPU", "仅使用 CPU"])
        
        btn_mdrun_nvt = QPushButton("2. mdrun (执行 NVT)")
        btn_mdrun_nvt.clicked.connect(self.run_mdrun_nvt)
        
        run_layout.addRow("预处理:", btn_grompp_nvt)
        run_layout.addRow("硬件加速:", self.nvt_gpu_combo)
        run_layout.addRow("执行计算:", btn_mdrun_nvt)
        
        run_group.setLayout(run_layout)
        layout.addWidget(run_group)

    def init_npt_tab(self):
        layout = QVBoxLayout(self.npt_tab)
        
        # 1. NPT MDP
        mdp_group = QGroupBox("1. 准备 NPT 参数 (npt.mdp)")
        mdp_layout = QVBoxLayout()
        
        self.npt_mdp_content = QTextEdit()
        default_npt_mdp = (
            "title                   = OPLS Lysozyme NPT equilibration \n"
            "define                  = -DPOSRES  ; position restrain the protein\n"
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
            "continuation            = yes       ; Restarting after NVT \n"
            "constraint_algorithm    = lincs     ; holonomic constraints \n"
            "constraints             = h-bonds   ; bonds involving H are constrained\n"
            "lincs_iter              = 1         ; accuracy of LINCS\n"
            "lincs_order             = 4         ; also related to accuracy\n"
            "; Nonbonded settings \n"
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
            "refcoord_scaling        = com\n"
            "; Periodic boundary conditions\n"
            "pbc                     = xyz       ; 3-D PBC\n"
            "; Velocity generation\n"
            "gen_vel                 = no        ; Velocity generation is off \n"
        )
        self.npt_mdp_content.setText(default_npt_mdp)
        self.npt_mdp_content.setStyleSheet("font-family: Consolas; font-size: 9pt;")
        
        btn_layout = QHBoxLayout()
        btn_edit_npt = QPushButton("打开参数编辑器")
        btn_edit_npt.clicked.connect(lambda: self.open_editor("npt"))
        
        btn_save_npt_mdp = QPushButton("保存为 npt.mdp")
        btn_save_npt_mdp.clicked.connect(lambda: self.save_mdp("npt.mdp", self.npt_mdp_content.toPlainText()))
        
        btn_layout.addWidget(btn_edit_npt)
        btn_layout.addWidget(btn_save_npt_mdp)
        
        mdp_layout.addWidget(self.npt_mdp_content)
        mdp_layout.addLayout(btn_layout)
        mdp_group.setLayout(mdp_layout)
        layout.addWidget(mdp_group)

        # 2. 运行 NPT
        run_group = QGroupBox("2. 运行 NPT 平衡")
        run_layout = QFormLayout()
        
        btn_grompp_npt = QPushButton("1. grompp (生成 npt.tpr)")
        btn_grompp_npt.clicked.connect(self.run_grompp_npt)
        
        self.npt_gpu_combo = QComboBox()
        self.npt_gpu_combo.addItems(["自动检测", "强制使用 GPU", "仅使用 CPU"])
        
        btn_mdrun_npt = QPushButton("2. mdrun (执行 NPT)")
        btn_mdrun_npt.clicked.connect(self.run_mdrun_npt)
        
        run_layout.addRow("预处理:", btn_grompp_npt)
        run_layout.addRow("硬件加速:", self.npt_gpu_combo)
        run_layout.addRow("执行计算:", btn_mdrun_npt)
        
        run_group.setLayout(run_layout)
        layout.addWidget(run_group)
    
    def open_editor(self, mdp_type):
        current_content = ""
        if mdp_type == "nvt":
            current_content = self.nvt_mdp_content.toPlainText()
        else:
            current_content = self.npt_mdp_content.toPlainText()
            
        dialog = MDPEditor(self, mdp_type, current_content)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_content = dialog.get_mdp_content()
            if mdp_type == "nvt":
                self.nvt_mdp_content.setText(new_content)
            else:
                self.npt_mdp_content.setText(new_content)

    def get_cwd(self):
        try:
            topo_tab = self.main_window.tabs.widget(0)
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

    def run_grompp_nvt(self):
        cwd = self.get_cwd()
        if not cwd:
            return
            
        required_files = ["nvt.mdp", "em.gro", "topol.top"]
        for f in required_files:
            if not os.path.exists(os.path.join(cwd, f)):
                QMessageBox.warning(self, "警告", f"缺少必要文件: {f}\n请确保已完成能量最小化步骤(em.gro)。")
                return

        # NVT 通常需要位置限制文件 posre.itp，它应该在 pdb2gmx 时生成
        args = ["grompp", "-f", "nvt.mdp", "-c", "em.gro", "-r", "em.gro", "-p", "topol.top", "-o", "nvt.tpr", "-maxwarn", "1"]
        
        self.main_window.log(f"\n>>> 正在运行: gmx {' '.join(args)}")
        success, output = self.runner.run_command(args, cwd=cwd)
        self.main_window.log(output)
        
        if success:
            QMessageBox.information(self, "成功", "grompp 运行完成！生成了 nvt.tpr")
        else:
            QMessageBox.critical(self, "错误", "grompp (NVT) 运行失败，请查看日志。")

    def run_mdrun_nvt(self):
        cwd = self.get_cwd()
        if not cwd: return
            
        if not os.path.exists(os.path.join(cwd, "nvt.tpr")):
            QMessageBox.warning(self, "警告", "未找到 nvt.tpr，请先运行 NVT grompp！")
            return

        args = ["mdrun", "-v", "-deffnm", "nvt"]
        gpu_opt = self.nvt_gpu_combo.currentText()
        if gpu_opt == "强制使用 GPU": args.extend(["-nb", "gpu"])
        elif gpu_opt == "仅使用 CPU": args.extend(["-nb", "cpu"])

        self.main_window.log(f"\n>>> 正在运行: gmx {' '.join(args)}")
        success, output = self.runner.run_command(args, cwd=cwd)
        self.main_window.log(output)
        
        if success:
            QMessageBox.information(self, "成功", "NVT 平衡完成！生成了 nvt.gro 等文件。")
        else:
            QMessageBox.critical(self, "错误", "mdrun (NVT) 运行失败，请查看日志。")

    def run_grompp_npt(self):
        cwd = self.get_cwd()
        if not cwd: return
            
        required_files = ["npt.mdp", "nvt.gro", "topol.top"]
        for f in required_files:
            if not os.path.exists(os.path.join(cwd, f)):
                QMessageBox.warning(self, "警告", f"缺少必要文件: {f}\n请确保已完成 NVT 步骤(nvt.gro)。")
                return

        args = ["grompp", "-f", "npt.mdp", "-c", "nvt.gro", "-r", "nvt.gro", "-t", "nvt.cpt", "-p", "topol.top", "-o", "npt.tpr", "-maxwarn", "1"]
        
        self.main_window.log(f"\n>>> 正在运行: gmx {' '.join(args)}")
        success, output = self.runner.run_command(args, cwd=cwd)
        self.main_window.log(output)
        
        if success:
            QMessageBox.information(self, "成功", "grompp 运行完成！生成了 npt.tpr")
        else:
            QMessageBox.critical(self, "错误", "grompp (NPT) 运行失败，请查看日志。")

    def run_mdrun_npt(self):
        cwd = self.get_cwd()
        if not cwd: return
            
        if not os.path.exists(os.path.join(cwd, "npt.tpr")):
            QMessageBox.warning(self, "警告", "未找到 npt.tpr，请先运行 NPT grompp！")
            return

        args = ["mdrun", "-v", "-deffnm", "npt"]
        gpu_opt = self.npt_gpu_combo.currentText()
        if gpu_opt == "强制使用 GPU": args.extend(["-nb", "gpu"])
        elif gpu_opt == "仅使用 CPU": args.extend(["-nb", "cpu"])

        self.main_window.log(f"\n>>> 正在运行: gmx {' '.join(args)}")
        success, output = self.runner.run_command(args, cwd=cwd)
        self.main_window.log(output)
        
        if success:
            QMessageBox.information(self, "成功", "NPT 平衡完成！生成了 npt.gro 等文件。")
        else:
            QMessageBox.critical(self, "错误", "mdrun (NPT) 运行失败，请查看日志。")
