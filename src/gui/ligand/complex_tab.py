from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QComboBox, QLineEdit, 
                             QMessageBox, QFileDialog, QCheckBox)
from PyQt6.QtCore import pyqtSignal
import os
import shutil

class ComplexTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.cwd = None
        
        self.ligand_itp = None
        self.ligand_gro = None
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 0. 状态信息
        self.status_label = QLabel("等待配体拓扑...")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.status_label)

        # 1. 处理受体蛋白 (pdb2gmx)
        pdb_group = QGroupBox("1. 处理受体蛋白 (pdb2gmx)")
        pdb_layout = QFormLayout()

        file_layout = QHBoxLayout()
        self.pdb_input = QLineEdit()
        self.pdb_input.setPlaceholderText("选择输入的蛋白 .pdb 文件...")
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self.browse_pdb)
        file_layout.addWidget(self.pdb_input)
        file_layout.addWidget(btn_browse)
        pdb_layout.addRow("受体 PDB:", file_layout)

        self.ff_combo = QComboBox()
        self.ff_combo.addItems(["amber03", "amber94", "amber96", "amber99", "amber99sb", "amber99sb-ildn", "charmm27", "oplsaa"])
        self.ff_combo.setCurrentText("oplsaa")
        pdb_layout.addRow("力场 (-ff):", self.ff_combo)

        self.water_combo = QComboBox()
        self.water_combo.addItems(["spce", "tip3p", "tip4p", "tip5p"])
        self.water_combo.setCurrentText("spce")
        pdb_layout.addRow("水模型 (-water):", self.water_combo)

        self.ignh_check = QCheckBox("忽略输入文件中的氢原子 (-ignh)")
        self.ignh_check.setChecked(True)
        pdb_layout.addRow("", self.ignh_check)

        btn_run_pdb2gmx = QPushButton("运行 pdb2gmx")
        btn_run_pdb2gmx.clicked.connect(self.run_pdb2gmx)
        pdb_layout.addRow("", btn_run_pdb2gmx)

        pdb_group.setLayout(pdb_layout)
        layout.addWidget(pdb_group)

        # 2. 构建复合物
        build_group = QGroupBox("2. 构建复合物")
        build_layout = QVBoxLayout()
        
        build_info = QLabel("将合并蛋白与配体坐标，并自动更新 topol.top。")
        build_layout.addWidget(build_info)
        
        btn_build_complex = QPushButton("合并生成复合物 (complex.gro & topol.top)")
        btn_build_complex.clicked.connect(self.build_complex)
        build_layout.addWidget(btn_build_complex)
        
        build_group.setLayout(build_layout)
        layout.addWidget(build_group)

        # 3. 定义盒子与溶剂化 (editconf & solvate)
        box_group = QGroupBox("3. 定义盒子与溶剂化")
        box_layout = QFormLayout()

        self.box_type = QComboBox()
        self.box_type.addItems(["cubic", "triclinic", "dodecahedron", "octahedron"])
        self.box_type.setCurrentText("cubic")
        box_layout.addRow("盒子形状 (-bt):", self.box_type)

        self.box_dist = QLineEdit("1.0")
        box_layout.addRow("边缘距离 (-d, nm):", self.box_dist)

        btn_run_box_solv = QPushButton("运行 editconf & solvate")
        btn_run_box_solv.clicked.connect(self.run_box_solv)
        box_layout.addRow("", btn_run_box_solv)

        box_group.setLayout(box_layout)
        layout.addWidget(box_group)

        # 4. 添加离子 (genion)
        genion_group = QGroupBox("4. 中和系统电荷 (genion)")
        genion_layout = QFormLayout()
        
        genion_info = QLabel("将自动运行 grompp 生成 ions.tpr，并使用 genion 替换水分子添加离子。")
        genion_layout.addRow(genion_info)

        self.conc_input = QLineEdit("0.15")
        genion_layout.addRow("盐浓度 (-conc, mol/L):", self.conc_input)

        self.pname_input = QLineEdit("NA")
        genion_layout.addRow("阳离子名称 (-pname):", self.pname_input)

        self.nname_input = QLineEdit("CL")
        genion_layout.addRow("阴离子名称 (-nname):", self.nname_input)
        
        self.neutral_check = QCheckBox("中和系统净电荷 (-neutral)")
        self.neutral_check.setChecked(True)
        genion_layout.addRow("", self.neutral_check)

        btn_run_genion = QPushButton("运行 grompp & genion")
        btn_run_genion.clicked.connect(self.run_genion)
        genion_layout.addRow("", btn_run_genion)
        
        genion_group.setLayout(genion_layout)
        layout.addWidget(genion_group)

        layout.addStretch()

    def update_ligand_info(self, cwd, itp_path, gro_path):
        self.cwd = cwd
        self.ligand_itp = os.path.basename(itp_path)
        self.ligand_gro = os.path.basename(gro_path)
        self.status_label.setText(f"✅ 已加载配体: {self.ligand_itp}, {self.ligand_gro} (工作目录: {self.cwd})")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")

    def browse_pdb(self):
        if not self.cwd:
            QMessageBox.warning(self, "警告", "请先在第一步【配体准备】中设置工作目录并导入配体！")
            return
        f, _ = QFileDialog.getOpenFileName(self, "选择蛋白 PDB 文件", self.cwd, "PDB Files (*.pdb)")
        if f:
            target_path = os.path.join(self.cwd, os.path.basename(f))
            if os.path.abspath(f) != os.path.abspath(target_path):
                shutil.copy(f, target_path)
            self.pdb_input.setText(os.path.basename(f))

    def set_buttons_enabled(self, enabled):
        for child in self.findChildren(QPushButton):
            child.setEnabled(enabled)

    def run_pdb2gmx(self):
        pdb_filename = self.pdb_input.text()
        if not pdb_filename or not self.cwd:
            QMessageBox.warning(self, "警告", "请选择蛋白文件或确保已设置工作目录。")
            return

        ff = self.ff_combo.currentText()
        water = self.water_combo.currentText()
        ignh = self.ignh_check.isChecked()

        args = ["pdb2gmx", "-f", pdb_filename, "-o", "protein.gro", "-p", "topol.top", "-ff", ff, "-water", water]
        if ignh:
            args.append("-ignh")

        self.worker_pdb2gmx = self.runner.create_worker(args, cwd=self.cwd)
        self.worker_pdb2gmx.output_signal.connect(self.main_window.log)
        self.worker_pdb2gmx.finished_signal.connect(self.on_pdb2gmx_finished)
        
        self.set_buttons_enabled(False)
        self.worker_pdb2gmx.start()

    def on_pdb2gmx_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "成功", "pdb2gmx 运行成功，已生成 protein.gro 和 topol.top")
        else:
            QMessageBox.critical(self, "错误", f"pdb2gmx 失败:\n{message}")

    def get_ligand_molecule_name(self, itp_path):
        """解析 itp 文件获取分子名称"""
        try:
            with open(itp_path, 'r') as f:
                lines = f.readlines()
            
            in_moleculetype = False
            for line in lines:
                line = line.strip()
                if line.startswith(';') or not line:
                    continue
                if line.startswith('[') and 'moleculetype' in line:
                    in_moleculetype = True
                    continue
                if in_moleculetype and not line.startswith('['):
                    parts = line.split()
                    if parts:
                        return parts[0]
                if in_moleculetype and line.startswith('['):
                    in_moleculetype = False
        except Exception as e:
            print(f"Error parsing ITP: {e}")
        return "UNL" # default fallback

    def build_complex(self):
        if not self.cwd or not self.ligand_gro or not self.ligand_itp:
            QMessageBox.warning(self, "警告", "配体信息缺失！")
            return
            
        prot_gro = os.path.join(self.cwd, "protein.gro")
        lig_gro = os.path.join(self.cwd, self.ligand_gro)
        comp_gro = os.path.join(self.cwd, "complex.gro")
        top_file = os.path.join(self.cwd, "topol.top")
        lig_itp_path = os.path.join(self.cwd, self.ligand_itp)
        
        if not os.path.exists(prot_gro) or not os.path.exists(top_file):
            QMessageBox.warning(self, "警告", "未找到 protein.gro 或 topol.top，请先运行 pdb2gmx！")
            return
            
        try:
            # 1. 合并 GRO 文件
            with open(prot_gro, 'r') as f:
                prot_lines = f.readlines()
            with open(lig_gro, 'r') as f:
                lig_lines = f.readlines()
                
            prot_atoms = int(prot_lines[1].strip())
            lig_atoms = int(lig_lines[1].strip())
            total_atoms = prot_atoms + lig_atoms
            
            with open(comp_gro, 'w') as f:
                f.write("Complex: Protein + Ligand\n")
                f.write(f"{total_atoms:5d}\n")
                # 写入蛋白原子 (去掉前两行和最后一行 box)
                f.writelines(prot_lines[2:-1])
                # 写入配体原子 (去掉前两行和最后一行 box)
                f.writelines(lig_lines[2:-1])
                # 写入 box 向量 (使用蛋白的)
                f.write(prot_lines[-1])
                
            # 2. 更新 TOP 文件
            with open(top_file, 'r') as f:
                top_lines = f.readlines()
                
            # 寻找插入 #include "ligand.itp" 的位置 (通常在力场 include 之后)
            insert_itp_idx = -1
            for i, line in enumerate(top_lines):
                if '#include' in line and ('forcefield.itp' in line or 'ffnonbonded.itp' in line):
                    insert_itp_idx = i
            
            lig_name = self.get_ligand_molecule_name(lig_itp_path)
            
            new_top_lines = []
            itp_inserted = False
            for i, line in enumerate(top_lines):
                new_top_lines.append(line)
                # 如果找到了 forcefield include，就在它后面插入
                if insert_itp_idx != -1 and i == insert_itp_idx and not itp_inserted:
                    new_top_lines.append(f'\n; Include ligand topology\n')
                    new_top_lines.append(f'#include "{self.ligand_itp}"\n\n')
                    itp_inserted = True
                # 如果没找到，就在 [ system ] 之前插入
                elif insert_itp_idx == -1 and '[ system ]' in line and not itp_inserted:
                    new_top_lines.insert(-1, f'; Include ligand topology\n#include "{self.ligand_itp}"\n\n')
                    itp_inserted = True
                    
            # 确保在文件末尾添加配体分子数量
            # 先检查是否已经有这个配体
            has_ligand_in_mols = False
            in_molecules_sec = False
            for line in new_top_lines:
                if '[ molecules ]' in line:
                    in_molecules_sec = True
                if in_molecules_sec and lig_name in line:
                    has_ligand_in_mols = True
                    
            if not has_ligand_in_mols:
                new_top_lines.append(f'{lig_name:<15} 1\n')
                
            with open(top_file, 'w') as f:
                f.writelines(new_top_lines)
                
            QMessageBox.information(self, "成功", f"复合物构建成功！\n已生成 complex.gro\n已更新 topol.top (添加了 {lig_name})")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"构建复合物时出错: {str(e)}")

    def run_box_solv(self):
        if not self.cwd: return
        bt = self.box_type.currentText()
        d = self.box_dist.text()
        
        # Editconf
        args_editconf = ["editconf", "-f", "complex.gro", "-o", "complex_newbox.gro", "-c", "-d", d, "-bt", bt]
        self.main_window.log(f"\n>>> 运行 editconf: {' '.join(args_editconf)}")
        
        self.worker_editconf = self.runner.create_worker(args_editconf, cwd=self.cwd)
        self.worker_editconf.output_signal.connect(self.main_window.log)
        self.worker_editconf.finished_signal.connect(self.on_editconf_finished)
        
        self.set_buttons_enabled(False)
        self.worker_editconf.start()

    def on_editconf_finished(self, success, message):
        if not success:
            self.set_buttons_enabled(True)
            QMessageBox.critical(self, "错误", f"editconf 失败:\n{message}")
            return
            
        # Solvate
        args_solvate = ["solvate", "-cp", "complex_newbox.gro", "-cs", "spc216.gro", "-o", "complex_solv.gro", "-p", "topol.top"]
        self.main_window.log(f"\n>>> 运行 solvate: {' '.join(args_solvate)}")
        
        self.worker_solvate = self.runner.create_worker(args_solvate, cwd=self.cwd)
        self.worker_solvate.output_signal.connect(self.main_window.log)
        self.worker_solvate.finished_signal.connect(self.on_solvate_finished)
        self.worker_solvate.start()

    def on_solvate_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "成功", "已完成定义盒子与溶剂化，生成 complex_solv.gro")
        else:
            QMessageBox.critical(self, "错误", f"solvate 失败:\n{message}")

    def run_genion(self):
        if not self.cwd: return
        
        # 先运行 grompp 生成 ions.tpr
        # 对于加离子，通常使用任意一个简单的 mdp 即可。我们创建一个临时的 ions.mdp
        ions_mdp_path = os.path.join(self.cwd, "ions.mdp")
        with open(ions_mdp_path, "w") as f:
            f.write("; ions.mdp - used as input into grompp to generate ions.tpr\n")
            f.write("integrator  = steep\n")
            f.write("emtol       = 1000.0\n")
            f.write("emstep      = 0.01\n")
            f.write("nsteps      = 50000\n")
            f.write("nstlist     = 1\n")
            f.write("cutoff-scheme = Verlet\n")
            f.write("ns_type     = grid\n")
            f.write("coulombtype = PME\n")
            f.write("rcoulomb    = 1.0\n")
            f.write("rvdw        = 1.0\n")
            f.write("pbc         = xyz\n")

        args_grompp = ["grompp", "-f", "ions.mdp", "-c", "complex_solv.gro", "-p", "topol.top", "-o", "ions.tpr", "-maxwarn", "2"]
        
        self.main_window.log(f"\n>>> 运行 grompp (为 genion 准备): {' '.join(args_grompp)}")
        self.worker_grompp = self.runner.create_worker(args_grompp, cwd=self.cwd)
        self.worker_grompp.output_signal.connect(self.main_window.log)
        self.worker_grompp.finished_signal.connect(self.on_genion_grompp_finished)
        
        self.set_buttons_enabled(False)
        self.worker_grompp.start()

    def on_genion_grompp_finished(self, success, message):
        if not success:
            self.set_buttons_enabled(True)
            QMessageBox.critical(self, "错误", f"grompp (ions) 失败:\n{message}")
            return
            
        # 运行 genion
        conc = self.conc_input.text()
        pname = self.pname_input.text()
        nname = self.nname_input.text()
        
        args_genion = ["genion", "-s", "ions.tpr", "-o", "complex_solv_ions.gro", "-p", "topol.top", "-pname", pname, "-nname", nname]
        if self.neutral_check.isChecked():
            args_genion.append("-neutral")
        if conc:
            args_genion.extend(["-conc", conc])
            
        self.main_window.log(f"\n>>> 运行 genion: {' '.join(args_genion)}")
        
        # genion 需要选择替换溶剂的组，通常选 13 (SOL) 或者 15 (Water)
        # 我们默认输入 13 试试，或者发送 "SOL"
        self.worker_genion = self.runner.create_worker(args_genion, cwd=self.cwd, input_text="SOL\n")
        self.worker_genion.output_signal.connect(self.main_window.log)
        self.worker_genion.finished_signal.connect(self.on_genion_finished)
        self.worker_genion.start()

    def on_genion_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "成功", "离子添加成功，生成 complex_solv_ions.gro！\n复合物系统准备完毕。")
        else:
            QMessageBox.critical(self, "错误", f"genion 失败:\n{message}")
