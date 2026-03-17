from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, 
                             QGroupBox, QFormLayout, QComboBox, 
                             QLineEdit, QCheckBox, QMessageBox)
import os

class TopologyTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window # Reference to main window for logging and running
        self.runner = main_window.runner
        self.cwd = None # Current working directory (usually the directory of the selected PDB)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 0. 工作目录和测试区
        test_group = QGroupBox("基础测试与环境")
        test_layout = QHBoxLayout()
        test_btn = QPushButton("测试 GROMACS 安装 (gmx -version)")
        test_btn.clicked.connect(self.main_window.test_gmx)
        test_layout.addWidget(test_btn)
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)

        # 1. PDB2GMX 区块
        pdb_group = QGroupBox("1. 生成拓扑 (pdb2gmx)")
        pdb_layout = QFormLayout()

        # 输入文件选择
        file_layout = QHBoxLayout()
        self.pdb_input = QLineEdit()
        self.pdb_input.setPlaceholderText("选择输入的 .pdb 文件...")
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self.browse_pdb)
        file_layout.addWidget(self.pdb_input)
        file_layout.addWidget(btn_browse)
        pdb_layout.addRow("输入 PDB:", file_layout)

        # 力场选择
        self.ff_combo = QComboBox()
        # 常见力场选项
        self.ff_combo.addItems(["amber03", "amber94", "amber96", "amber99", "amber99sb", "amber99sb-ildn", "charmm27", "oplsaa"])
        self.ff_combo.setCurrentText("oplsaa")
        pdb_layout.addRow("力场 (-ff):", self.ff_combo)

        # 水模型选择
        self.water_combo = QComboBox()
        self.water_combo.addItems(["spce", "tip3p", "tip4p", "tip5p"])
        self.water_combo.setCurrentText("spce")
        pdb_layout.addRow("水模型 (-water):", self.water_combo)

        # 忽略氢原子
        self.ignh_check = QCheckBox("忽略输入文件中的氢原子 (-ignh)")
        self.ignh_check.setChecked(True)
        pdb_layout.addRow("", self.ignh_check)

        # 执行按钮
        btn_run_pdb2gmx = QPushButton("运行 pdb2gmx")
        btn_run_pdb2gmx.clicked.connect(self.run_pdb2gmx)
        pdb_layout.addRow("", btn_run_pdb2gmx)

        pdb_group.setLayout(pdb_layout)
        layout.addWidget(pdb_group)

        # 2. EDITCONF 区块 (定义盒子)
        box_group = QGroupBox("2. 定义盒子 (editconf)")
        box_layout = QFormLayout()

        self.box_type = QComboBox()
        self.box_type.addItems(["cubic", "triclinic", "dodecahedron", "octahedron"])
        self.box_type.setCurrentText("cubic")
        box_layout.addRow("盒子形状 (-bt):", self.box_type)

        self.box_dist = QLineEdit("1.0")
        box_layout.addRow("边缘距离 (-d, nm):", self.box_dist)

        btn_run_editconf = QPushButton("运行 editconf")
        btn_run_editconf.clicked.connect(self.run_editconf)
        box_layout.addRow("", btn_run_editconf)

        box_group.setLayout(box_layout)
        layout.addWidget(box_group)

        # 3. SOLVATE 区块 (添加溶剂)
        solvate_group = QGroupBox("3. 添加溶剂 (solvate)")
        solvate_layout = QFormLayout()

        btn_run_solvate = QPushButton("运行 solvate")
        btn_run_solvate.clicked.connect(self.run_solvate)
        solvate_layout.addRow("", btn_run_solvate)

        solvate_group.setLayout(solvate_layout)
        layout.addWidget(solvate_group)
        
        # 4. GENION 区块 (添加离子)
        genion_group = QGroupBox("4. 添加离子中和系统 (genion)")
        genion_layout = QFormLayout()
        
        # 为了运行 genion，我们需要先运行一个只生成 tpr 的 grompp
        # 所以我提供一个一键按钮：先 grompp 生成 ions.tpr，再 genion
        self.pname_input = QLineEdit("NA")
        self.nname_input = QLineEdit("CL")
        self.conc_input = QLineEdit("0.15")
        self.neutral_check = QCheckBox("自动中和系统电荷 (-neutral)")
        self.neutral_check.setChecked(True)
        
        genion_layout.addRow("阳离子名称 (-pname):", self.pname_input)
        genion_layout.addRow("阴离子名称 (-nname):", self.nname_input)
        genion_layout.addRow("盐浓度 (-conc, mol/L):", self.conc_input)
        genion_layout.addRow("", self.neutral_check)
        
        btn_run_genion = QPushButton("运行 genion (先 grompp 后 genion)")
        btn_run_genion.clicked.connect(self.run_genion)
        genion_layout.addRow("", btn_run_genion)
        
        genion_group.setLayout(genion_layout)
        layout.addWidget(genion_group)

        layout.addStretch()

    def browse_pdb(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择 PDB 文件", "", "PDB Files (*.pdb);;All Files (*)")
        if file_path:
            self.pdb_input.setText(file_path)
            self.cwd = os.path.dirname(file_path)
            self.main_window.log(f"已设置工作目录为: {self.cwd}")

    def set_buttons_enabled(self, enabled):
        """启用或禁用所有按钮，防止重复提交任务"""
        for child in self.findChildren(QPushButton):
            child.setEnabled(enabled)

    def run_pdb2gmx(self):
        pdb_file = self.pdb_input.text()
        if not pdb_file or not os.path.exists(pdb_file):
            QMessageBox.warning(self, "警告", "请先选择有效的 PDB 文件！")
            return

        self.cwd = os.path.dirname(pdb_file)
        
        ff = self.ff_combo.currentText()
        water = self.water_combo.currentText()
        ignh = self.ignh_check.isChecked()

        # 提取文件名(不含路径)
        pdb_filename = os.path.basename(pdb_file)

        args = ["pdb2gmx", "-f", pdb_filename, "-o", "processed.gro", "-p", "topol.top", "-ff", ff, "-water", water]
        if ignh:
            args.append("-ignh")

        # 使用异步 Worker 执行
        self.worker_pdb2gmx = self.runner.create_worker(args, cwd=self.cwd)
        self.worker_pdb2gmx.output_signal.connect(self.main_window.log)
        self.worker_pdb2gmx.finished_signal.connect(self.on_pdb2gmx_finished)
        
        self.set_buttons_enabled(False)
        self.worker_pdb2gmx.start()

    def on_pdb2gmx_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "成功", "pdb2gmx 运行完成！生成了 processed.gro 和 topol.top")
        else:
            QMessageBox.critical(self, "错误", f"pdb2gmx 运行失败: {message}")

    def run_editconf(self):
        if not self.cwd:
            QMessageBox.warning(self, "警告", "请先完成 pdb2gmx 步骤或设置工作目录！")
            return
            
        gro_file = os.path.join(self.cwd, "processed.gro")
        if not os.path.exists(gro_file):
            QMessageBox.warning(self, "警告", f"未找到 processed.gro，请确保上一阶段已成功执行！\n期望路径: {gro_file}")
            return

        bt = self.box_type.currentText()
        d = self.box_dist.text()

        args = ["editconf", "-f", "processed.gro", "-o", "newbox.gro", "-c", "-d", d, "-bt", bt]

        # 使用异步 Worker 执行
        self.worker_editconf = self.runner.create_worker(args, cwd=self.cwd)
        self.worker_editconf.output_signal.connect(self.main_window.log)
        self.worker_editconf.finished_signal.connect(self.on_editconf_finished)
        
        self.set_buttons_enabled(False)
        self.worker_editconf.start()

    def on_editconf_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "成功", "editconf 运行完成！生成了 newbox.gro")
        else:
            QMessageBox.critical(self, "错误", f"editconf 运行失败: {message}")

    def run_solvate(self):
        if not self.cwd:
            QMessageBox.warning(self, "警告", "请先完成上述步骤或设置工作目录！")
            return
            
        gro_file = os.path.join(self.cwd, "newbox.gro")
        top_file = os.path.join(self.cwd, "topol.top")
        
        if not os.path.exists(gro_file) or not os.path.exists(top_file):
            QMessageBox.warning(self, "警告", "未找到 newbox.gro 或 topol.top，请确保上一阶段已成功执行！")
            return

        # 默认使用 spc216.gro 作为溶剂盒子
        args = ["solvate", "-cp", "newbox.gro", "-cs", "spc216.gro", "-o", "solvated.gro", "-p", "topol.top"]

        # 使用异步 Worker 执行
        self.worker_solvate = self.runner.create_worker(args, cwd=self.cwd)
        self.worker_solvate.output_signal.connect(self.main_window.log)
        self.worker_solvate.finished_signal.connect(self.on_solvate_finished)
        
        self.set_buttons_enabled(False)
        self.worker_solvate.start()

    def on_solvate_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "成功", "solvate 运行完成！生成了 solvated.gro")
        else:
            QMessageBox.critical(self, "错误", f"solvate 运行失败: {message}")

    def run_genion(self):
        if not self.cwd:
            QMessageBox.warning(self, "警告", "请先完成上述步骤！")
            return
            
        # 1. 首先需要生成一个离子的 mdp 文件 (最简单的即可)
        ions_mdp = os.path.join(self.cwd, "ions.mdp")
        if not os.path.exists(ions_mdp):
            try:
                with open(ions_mdp, "w") as f:
                    f.write("; ions.mdp - used as input into grompp to generate ions.tpr\n")
                    f.write("integrator  = steep\n")
                    f.write("emtol       = 1000.0\n")
                    f.write("emstep      = 0.01\n")
                    f.write("nsteps      = 50000\n")
                    f.write("nstlist         = 1\n")
                    f.write("cutoff-scheme   = Verlet\n")
                    f.write("ns_type         = grid\n")
                    f.write("coulombtype     = cutoff\n")
                    f.write("rcoulomb        = 1.0\n")
                    f.write("rvdw            = 1.0\n")
                    f.write("pbc             = xyz\n")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建 ions.mdp 失败: {str(e)}")
                return
        
        # 2. 运行 grompp 生成 ions.tpr
        args_grompp = ["grompp", "-f", "ions.mdp", "-c", "solvated.gro", "-p", "topol.top", "-o", "ions.tpr"]
        # 忽略 maxwarn 防止刚才的报错打断离子生成
        args_grompp.append("-maxwarn")
        args_grompp.append("1")
        
        self.worker_genion_grompp = self.runner.create_worker(args_grompp, cwd=self.cwd)
        self.worker_genion_grompp.output_signal.connect(self.main_window.log)
        self.worker_genion_grompp.finished_signal.connect(self.on_genion_grompp_finished)
        
        self.set_buttons_enabled(False)
        self.worker_genion_grompp.start()

    def on_genion_grompp_finished(self, success, message):
        if not success:
            self.set_buttons_enabled(True)
            QMessageBox.critical(self, "错误", f"生成 ions.tpr 失败: {message}")
            return
            
        # 3. 运行 genion
        pname = self.pname_input.text()
        nname = self.nname_input.text()
        conc = self.conc_input.text()
        neutral = self.neutral_check.isChecked()
        
        args_genion = ["genion", "-s", "ions.tpr", "-o", "solvated_ions.gro", "-p", "topol.top", 
                       "-pname", pname, "-nname", nname, "-conc", conc]
        if neutral:
            args_genion.append("-neutral")
            
        # 使用 input_text="SOL" 自动选择溶剂组
        self.worker_genion = self.runner.create_worker(args_genion, cwd=self.cwd, input_text="SOL")
        self.worker_genion.output_signal.connect(self.main_window.log)
        self.worker_genion.finished_signal.connect(self.on_genion_finished)
        
        self.worker_genion.start()

    def on_genion_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "成功", "genion 运行完成！生成了 solvated_ions.gro，并已更新拓扑。")
            QMessageBox.information(self, "注意", "现在您已经添加了离子，后续的能量最小化请使用 [solvated_ions.gro] 作为输入！")
        else:
            QMessageBox.critical(self, "错误", f"genion 运行失败: {message}\n可能是找不到 'SOL' 组。")
