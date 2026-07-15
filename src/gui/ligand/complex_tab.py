from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QComboBox, QLineEdit, 
                             QMessageBox, QFileDialog, QCheckBox)
from PyQt6.QtCore import pyqtSignal
import os
import shutil

# 标准蛋白残基 3 字母代码
STANDARD_RESIDUES = {
    "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS",
    "ILE", "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP",
    "TYR", "VAL",
    # 常见质子化变体 / N/C 端
    "HID", "HIE", "HIP", "CYM", "CYX", "ASH", "GLH", "LYN",
    # DNA/RNA (如果用户做蛋白-核酸体系)
    "DA", "DC", "DG", "DT", "A", "C", "G", "U",
    "DA5", "DC5", "DG5", "DT5", "DA3", "DC3", "DG3", "DT3",
    "A5", "C5", "G5", "U5", "A3", "C3", "G3", "U3",
}

# 溶剂/离子残基名 (拆分时跳过)
SKIP_RESIDUES = {
    "HOH", "WAT", "SOL", "TIP", "TIP3", "SPC", "NA", "CL", "K",
    "CA", "MG", "ZN", "FE", "MN", "CO", "NI", "CU", "CD", "SO4",
    "PO4", "ACT", "GOL", "EDO", "MPD", "PEG", "PG4",
}

class ComplexTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.cwd = None
        
        self.ligand_itp = "ligand.itp"
        self.ligand_resname = None  # 配体残基名，拆分时识别
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 0. 状态信息
        self.status_label = QLabel("等待配体拓扑导入... (请先完成「1. 配体准备」标签页)")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.status_label)

        # 1. 选择复合物 PDB 并拆分
        complex_group = QGroupBox("1. 选择复合物 PDB 并拆分")
        complex_layout = QFormLayout()

        file_layout = QHBoxLayout()
        self.complex_input = QLineEdit()
        self.complex_input.setPlaceholderText("选择复合物 .pdb 文件 (包含蛋白与配体)...")
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self.browse_complex)
        file_layout.addWidget(self.complex_input)
        file_layout.addWidget(btn_browse)
        complex_layout.addRow("复合物 PDB:", file_layout)

        self.split_info = QLabel("选择复合物 PDB 后，程序将自动识别并拆分蛋白与配体。")
        self.split_info.setStyleSheet("color: #555; font-style: italic;")
        complex_layout.addRow(self.split_info)

        btn_split = QPushButton("自动拆分并生成 protein.pdb & ligand.gro")
        btn_split.clicked.connect(self.split_complex_pdb)
        complex_layout.addRow("", btn_split)

        complex_group.setLayout(complex_layout)
        layout.addWidget(complex_group)

        # 2. 处理受体蛋白 (pdb2gmx)
        pdb_group = QGroupBox("2. 处理受体蛋白 (pdb2gmx)")
        pdb_layout = QFormLayout()

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

        # 3. 构建复合物
        build_group = QGroupBox("3. 构建复合物")
        build_layout = QVBoxLayout()
        
        build_info = QLabel("将蛋白与配体坐标合并为 complex.gro，并更新 topol.top。\n(蛋白与配体坐标来自同一复合物 PDB，空间关系已确定。)")
        build_info.setStyleSheet("color: #555; font-style: italic;")
        build_layout.addWidget(build_info)
        
        btn_build_complex = QPushButton("合并生成复合物 (complex.gro & topol.top)")
        btn_build_complex.clicked.connect(self.build_complex)
        build_layout.addWidget(btn_build_complex)
        
        build_group.setLayout(build_layout)
        layout.addWidget(build_group)

        # 4. 定义盒子与溶剂化 (editconf & solvate)
        box_group = QGroupBox("4. 定义盒子与溶剂化")
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

        # 5. 添加离子 (genion)
        genion_group = QGroupBox("5. 中和系统电荷 (genion)")
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

    # ------------------------------------------------------------------
    # 信号接收：从 LigandPrepTab 传来工作目录和 itp 路径
    # ------------------------------------------------------------------
    def update_ligand_info(self, cwd, itp_path):
        self.cwd = cwd
        self.ligand_itp = os.path.basename(itp_path)
        self.status_label.setText(f"✅ 已加载配体拓扑: {self.ligand_itp} (工作目录: {self.cwd})")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------
    def set_buttons_enabled(self, enabled):
        for child in self.findChildren(QPushButton):
            child.setEnabled(enabled)

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
        return "LIG"

    # ------------------------------------------------------------------
    # 浏览复合物 PDB
    # ------------------------------------------------------------------
    def browse_complex(self):
        if not self.cwd:
            QMessageBox.warning(self, "警告", "请先在「1. 配体准备」标签页中导入配体 .itp 并设置工作目录！")
            return
        f, _ = QFileDialog.getOpenFileName(self, "选择复合物 PDB 文件", self.cwd, "PDB Files (*.pdb)")
        if f:
            target_path = os.path.join(self.cwd, os.path.basename(f))
            if os.path.abspath(f) != os.path.abspath(target_path):
                shutil.copy(f, target_path)
            self.complex_input.setText(os.path.basename(f))

    # ------------------------------------------------------------------
    # 拆分复合物 PDB → protein.pdb + ligand.gro
    # ------------------------------------------------------------------
    def split_complex_pdb(self):
        pdb_filename = self.complex_input.text()
        if not pdb_filename or not self.cwd:
            QMessageBox.warning(self, "警告", "请先选择复合物 PDB 文件。")
            return

        complex_path = os.path.join(self.cwd, pdb_filename)
        if not os.path.exists(complex_path):
            QMessageBox.warning(self, "警告", f"未找到文件: {complex_path}")
            return

        try:
            with open(complex_path, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取复合物 PDB 失败: {str(e)}")
            return

        protein_lines = []
        ligand_atoms = []
        box_line = None
        seen_residues = set()

        for line in lines:
            if line.startswith("ATOM") or line.startswith("HETATM"):
                resname = line[17:20].strip()
                seen_residues.add(resname)

                if resname in SKIP_RESIDUES:
                    continue
                elif resname in STANDARD_RESIDUES:
                    protein_lines.append(line)
                else:
                    # 非标准残基 → 归类为配体
                    ligand_atoms.append(line)
                    self.ligand_resname = resname

            elif line.startswith("CRYST1") or line.startswith("SCALE"):
                # box 信息，保留给 ligand.gro
                box_line = line
            elif line.startswith("END") or line.startswith("TER"):
                continue

        # 检查结果
        if not protein_lines:
            QMessageBox.warning(self, "警告",
                "未在复合物 PDB 中识别到任何标准蛋白残基。\n"
                f"检测到的残基: {', '.join(sorted(seen_residues)) if seen_residues else '无'}")
            return

        if not ligand_atoms:
            QMessageBox.warning(self, "警告",
                "未在复合物 PDB 中识别到非标准配体残基。\n"
                f"检测到的残基: {', '.join(sorted(seen_residues)) if seen_residues else '无'}\n"
                "配体必须是蛋白/核酸/溶剂/离子以外的残基名。")
            return

        # 写入 protein.pdb
        protein_path = os.path.join(self.cwd, "protein.pdb")
        with open(protein_path, 'w') as f:
            f.writelines(protein_lines)
            f.write("END\n")

        # 写入 ligand.gro (GRO 格式更简单，避免 PDB→GRO 二次转换)
        ligand_gro_path = os.path.join(self.cwd, "ligand.gro")
        with open(ligand_gro_path, 'w') as f:
            f.write(f"Ligand: {self.ligand_resname}\n")
            f.write(f"{len(ligand_atoms):5d}\n")
            for atom_line in ligand_atoms:
                # PDB ATOM 行 → 简化的 GRO 行
                # GRO 格式: %5d%-5s%5s%5d%8.3f%8.3f%8.3f
                atom_num = int(atom_line[6:11].strip())
                atom_name = atom_line[12:16].strip()
                resname = atom_line[17:20].strip()
                resid = int(atom_line[22:26].strip())
                x = float(atom_line[30:38].strip())
                y = float(atom_line[38:46].strip())
                z = float(atom_line[46:54].strip())
                f.write(f"{resid:5d}{resname:<5s}{atom_name:>5s}{atom_num:5d}{x:8.3f}{y:8.3f}{z:8.3f}\n")
            # box 向量
            if box_line and len(box_line) >= 54:
                try:
                    a = float(box_line[6:15].strip())
                    b = float(box_line[15:24].strip())
                    c = float(box_line[24:33].strip())
                    f.write(f"    {a:.5f} {b:.5f} {c:.5f}\n")
                except ValueError:
                    f.write("    10.00000   10.00000   10.00000\n")
            else:
                f.write("    10.00000   10.00000   10.00000\n")

        self.split_info.setText(
            f"✅ 拆分完成！\n"
            f"  蛋白: protein.pdb ({len(protein_lines)} 个原子)\n"
            f"  配体: ligand.gro ({len(ligand_atoms)} 个原子, 残基名: {self.ligand_resname})")
        self.split_info.setStyleSheet("color: green; font-weight: bold;")
        self.main_window.log(f"拆分复合物: 蛋白 {len(protein_lines)} 原子, 配体 {len(ligand_atoms)} 原子 ({self.ligand_resname})")

    # ------------------------------------------------------------------
    # 运行 pdb2gmx (蛋白)
    # ------------------------------------------------------------------
    def run_pdb2gmx(self):
        protein_pdb = os.path.join(self.cwd, "protein.pdb")
        if not os.path.exists(protein_pdb):
            QMessageBox.warning(self, "警告", "未找到 protein.pdb，请先拆分复合物 PDB！")
            return

        if not self.cwd:
            QMessageBox.warning(self, "警告", "未设置工作目录。")
            return

        ff = self.ff_combo.currentText()
        water = self.water_combo.currentText()
        ignh = self.ignh_check.isChecked()

        args = ["pdb2gmx", "-f", "protein.pdb", "-o", "protein.gro", "-p", "topol.top", "-ff", ff, "-water", water]
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

    # ------------------------------------------------------------------
    # 构建复合物：合并蛋白 + 配体坐标，更新 topol.top
    # ------------------------------------------------------------------
    def build_complex(self):
        if not self.cwd or not self.ligand_itp:
            QMessageBox.warning(self, "警告", "配体拓扑信息缺失！请先完成「1. 配体准备」。")
            return
            
        prot_gro = os.path.join(self.cwd, "protein.gro")
        lig_gro = os.path.join(self.cwd, "ligand.gro")
        comp_gro = os.path.join(self.cwd, "complex.gro")
        top_file = os.path.join(self.cwd, "topol.top")
        lig_itp_path = os.path.join(self.cwd, self.ligand_itp)
        
        if not os.path.exists(prot_gro) or not os.path.exists(top_file):
            QMessageBox.warning(self, "警告", "未找到 protein.gro 或 topol.top，请先运行 pdb2gmx！")
            return
        
        if not os.path.exists(lig_gro):
            QMessageBox.warning(self, "警告", "未找到 ligand.gro，请先拆分复合物 PDB！")
            return
            
        try:
            # 1. 合并 GRO 文件 (protein.gro + ligand.gro)
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
                f.writelines(prot_lines[2:-1])
                f.writelines(lig_lines[2:-1])
                f.write(prot_lines[-1])
                
            # 2. 更新 TOP 文件
            with open(top_file, 'r') as f:
                top_lines = f.readlines()
                
            insert_itp_idx = -1
            for i, line in enumerate(top_lines):
                if '#include' in line and ('forcefield.itp' in line or 'ffnonbonded.itp' in line):
                    insert_itp_idx = i
            
            lig_name = self.get_ligand_molecule_name(lig_itp_path)
            include_line = f'#include "{self.ligand_itp}"'
            ligand_include_exists = any(include_line in line for line in top_lines)
            
            new_top_lines = []
            itp_inserted = False
            for i, line in enumerate(top_lines):
                new_top_lines.append(line)
                if insert_itp_idx != -1 and i == insert_itp_idx and not itp_inserted and not ligand_include_exists:
                    new_top_lines.append(f'\n; Include ligand topology\n')
                    new_top_lines.append(f'#include "{self.ligand_itp}"\n\n')
                    itp_inserted = True
                elif insert_itp_idx == -1 and '[ system ]' in line and not itp_inserted and not ligand_include_exists:
                    new_top_lines.insert(-1, f'; Include ligand topology\n#include "{self.ligand_itp}"\n\n')
                    itp_inserted = True
                    
            # 在 [ molecules ] 中按坐标顺序插入配体
            has_ligand_in_mols = False
            in_molecules_sec = False
            molecules_header_idx = -1
            for i, line in enumerate(new_top_lines):
                if '[ molecules ]' in line:
                    in_molecules_sec = True
                    molecules_header_idx = i
                if in_molecules_sec and lig_name in line:
                    has_ligand_in_mols = True
                    
            if not has_ligand_in_mols:
                insert_mol_idx = len(new_top_lines)
                if molecules_header_idx != -1:
                    insert_mol_idx = molecules_header_idx + 1
                    for i in range(molecules_header_idx + 1, len(new_top_lines)):
                        stripped = new_top_lines[i].strip()
                        if not stripped or stripped.startswith(';'):
                            continue
                        parts = stripped.split()
                        mol_name = parts[0] if parts else ""
                        if mol_name in {"SOL", "WAT", "HOH", "NA", "CL", "K", "CA", "MG"}:
                            insert_mol_idx = i
                            break
                        insert_mol_idx = i + 1
                new_top_lines.insert(insert_mol_idx, f'{lig_name:<15} 1\n')
                
            with open(top_file, 'w') as f:
                f.writelines(new_top_lines)
                
            QMessageBox.information(self, "成功", f"复合物构建成功！\n已生成 complex.gro\n已更新 topol.top (添加了 {lig_name})")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"构建复合物时出错: {str(e)}")

    # ------------------------------------------------------------------
    # 溶剂化 + 加离子 (与之前基本一致)
    # ------------------------------------------------------------------
    def run_box_solv(self):
        if not self.cwd: return
        bt = self.box_type.currentText()
        d = self.box_dist.text()
        
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
            
        conc = self.conc_input.text()
        pname = self.pname_input.text()
        nname = self.nname_input.text()
        
        args_genion = ["genion", "-s", "ions.tpr", "-o", "complex_solv_ions.gro", "-p", "topol.top", "-pname", pname, "-nname", nname]
        if self.neutral_check.isChecked():
            args_genion.append("-neutral")
        if conc:
            args_genion.extend(["-conc", conc])
            
        self.main_window.log(f"\n>>> 运行 genion: {' '.join(args_genion)}")
        
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
