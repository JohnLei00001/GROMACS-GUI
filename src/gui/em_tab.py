from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, 
                             QGroupBox, QFormLayout, QComboBox, 
                             QLineEdit, QTextEdit, QMessageBox, QDialog)
import os
from .mdp_editor import MDPEditor

class EMTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. MDP 文件准备
        mdp_group = QGroupBox("1. 准备能量最小化参数 (minim.mdp)")
        mdp_layout = QVBoxLayout()
        
        self.mdp_content = QTextEdit()
        # 默认的能量最小化参数
        default_mdp = (
            "; minim.mdp - used as input into grompp to generate em.tpr\n"
            "integrator  = steep         ; Algorithm (steep = steepest descent minimization)\n"
            "emtol       = 1000.0        ; Stop minimization when the maximum force < 1000.0 kJ/mol/nm\n"
            "emstep      = 0.01          ; Minimization step size\n"
            "nsteps      = 50000         ; Maximum number of (minimization) steps to perform\n"
            "\n"
            "; Parameters describing how to find the neighbors of each atom and how to calculate the interactions\n"
            "nstlist         = 1         ; Frequency to update the neighbor list and long range forces\n"
            "cutoff-scheme   = Verlet    ; Buffered neighbor searching\n"
            "ns_type         = grid      ; Method to determine neighbor list (simple, grid)\n"
            "coulombtype     = PME       ; Treatment of long range electrostatic interactions\n"
            "rcoulomb        = 1.0       ; Short-range electrostatic cut-off\n"
            "rvdw            = 1.0       ; Short-range Van der Waals cut-off\n"
            "pbc             = xyz       ; Periodic Boundary Conditions in all directions\n"
        )
        self.mdp_content.setText(default_mdp)
        self.mdp_content.setStyleSheet("font-family: Consolas; font-size: 9pt;")
        
        btn_layout = QHBoxLayout()
        btn_edit_mdp = QPushButton("打开参数编辑器")
        btn_edit_mdp.clicked.connect(self.open_editor)
        
        btn_save_mdp = QPushButton("保存为 minim.mdp")
        btn_save_mdp.clicked.connect(self.save_mdp)
        
        btn_layout.addWidget(btn_edit_mdp)
        btn_layout.addWidget(btn_save_mdp)
        
        mdp_layout.addWidget(QLabel("MDP 参数内容:"))
        mdp_layout.addWidget(self.mdp_content)
        mdp_layout.addLayout(btn_layout)
        mdp_group.setLayout(mdp_layout)
        layout.addWidget(mdp_group)

        # 2. GROMPP 区块
        grompp_group = QGroupBox("2. 生成运行文件 (grompp)")
        grompp_layout = QFormLayout()
        
        btn_run_grompp = QPushButton("运行 grompp")
        btn_run_grompp.clicked.connect(self.run_grompp)
        grompp_layout.addRow("执行预处理:", btn_run_grompp)
        
        grompp_group.setLayout(grompp_layout)
        layout.addWidget(grompp_group)

        # 3. MDRUN 区块
        mdrun_group = QGroupBox("3. 执行能量最小化 (mdrun)")
        mdrun_layout = QFormLayout()
        
        self.gpu_check = QComboBox()
        self.gpu_check.addItems(["自动检测", "强制使用 GPU", "仅使用 CPU"])
        mdrun_layout.addRow("硬件加速:", self.gpu_check)
        
        btn_run_mdrun = QPushButton("运行 mdrun")
        btn_run_mdrun.clicked.connect(self.run_mdrun)
        mdrun_layout.addRow("执行计算:", btn_run_mdrun)
        
        mdrun_group.setLayout(mdrun_layout)
        layout.addWidget(mdrun_group)

        layout.addStretch()

    def get_cwd(self):
        # 尝试从 TopologyTab 获取工作目录
        try:
            # 假设 TopologyTab 是第一个标签页
            topo_tab = self.main_window.tabs.widget(0)
            return topo_tab.cwd
        except:
            return None

    def save_mdp(self):
        cwd = self.get_cwd()
        if not cwd:
            QMessageBox.warning(self, "警告", "请先在'拓扑与水箱'步骤中选择文件以确定工作目录！")
            return
            
        mdp_path = os.path.join(cwd, "minim.mdp")
        try:
            with open(mdp_path, "w") as f:
                f.write(self.mdp_content.toPlainText())
            self.main_window.log(f"已成功保存 MDP 文件: {mdp_path}")
            QMessageBox.information(self, "成功", "minim.mdp 已保存。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存 MDP 文件失败: {str(e)}")

    def run_grompp(self):
        cwd = self.get_cwd()
        if not cwd:
            QMessageBox.warning(self, "警告", "请先确定工作目录！")
            return
            
        # 检查输入文件是否存在
        # 优先使用加了离子的 solvated_ions.gro，如果没有则使用 solvated.gro
        input_gro = "solvated.gro"
        if os.path.exists(os.path.join(cwd, "solvated_ions.gro")):
            input_gro = "solvated_ions.gro"
            self.main_window.log("检测到 solvated_ions.gro，将使用添加离子后的结构进行能量最小化。")
            
        required_files = ["minim.mdp", input_gro, "topol.top"]
        for f in required_files:
            if not os.path.exists(os.path.join(cwd, f)):
                QMessageBox.warning(self, "警告", f"缺少必要文件: {f}\n请确保已完成之前的步骤。")
                return

        args = ["grompp", "-f", "minim.mdp", "-c", input_gro, "-p", "topol.top", "-o", "em.tpr", "-maxwarn", "1"]
        
        self.main_window.log(f"\n>>> 正在运行: gmx {' '.join(args)}")
        
        # 使用异步 Worker 执行
        self.worker = self.runner.create_worker(args, cwd=cwd)
        self.worker.output_signal.connect(self.main_window.log)
        self.worker.finished_signal.connect(self.on_grompp_finished)
        
        # 禁用按钮防止重复点击
        self.set_buttons_enabled(False)
        self.worker.start()

    def on_grompp_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "成功", "grompp 运行完成！生成了 em.tpr")
        else:
            QMessageBox.critical(self, "错误", f"grompp 运行失败: {message}")

    def set_buttons_enabled(self, enabled):
        # 简单粗暴地禁用/启用所有按钮
        for child in self.findChildren(QPushButton):
            child.setEnabled(enabled)

    def open_editor(self):
        current_content = self.mdp_content.toPlainText()
        dialog = MDPEditor(self, "em", current_content)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_content = dialog.get_mdp_content()
            self.mdp_content.setPlainText(new_content)

    def run_mdrun(self):
        cwd = self.get_cwd()
        if not cwd:
            QMessageBox.warning(self, "警告", "请先确定工作目录！")
            return
            
        if not os.path.exists(os.path.join(cwd, "em.tpr")):
            QMessageBox.warning(self, "警告", "未找到 em.tpr，请先运行 grompp！")
            return

        args = ["mdrun", "-v", "-deffnm", "em"]
        
        # 根据 GPU 选项添加参数
        gpu_opt = self.gpu_check.currentText()
        if gpu_opt == "强制使用 GPU":
            args.extend(["-nb", "gpu"])
        elif gpu_opt == "仅使用 CPU":
            args.extend(["-nb", "cpu"])

        self.main_window.log(f"\n>>> 正在运行: gmx {' '.join(args)}")
        
        # 使用异步 Worker 执行
        self.worker = self.runner.create_worker(args, cwd=cwd)
        self.worker.output_signal.connect(self.main_window.log)
        self.worker.finished_signal.connect(self.on_mdrun_finished)
        
        self.set_buttons_enabled(False)
        self.worker.start()

    def on_mdrun_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "成功", "EM 能量最小化完成！")
        else:
            QMessageBox.critical(self, "错误", f"mdrun (EM) 运行失败: {message}")
