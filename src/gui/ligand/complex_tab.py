from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, 
                             QFormLayout, QComboBox, QLineEdit, 
                             QMessageBox, QFileDialog, QCheckBox,
                             QScrollArea, QFrame)
from PyQt6.QtCore import pyqtSignal
from gui.topology_tab import discover_forcefields, strip_pdb_nonprotein
import os
import shutil

from gui.i18n import tr, trf
from gui.theme import set_role
from gui.widgets import StepCard

class ComplexTab(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.runner = main_window.runner
        self.cwd = None
        
        self.ligand_itp = "ligand.itp"
        self.ligand_gro = "ligand.gro"
        
        self.init_ui()

    def init_ui(self):
        # 滚动容器：内容超高时允许滚动，避免窗口拉矮后被裁切
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget(); layout = QVBoxLayout(w)
        layout.setSpacing(10)

        # 0. 状态信息
        self.status_label = QLabel(tr("等待配体导入... (请先完成「1. 配体准备」标签页)"))
        set_role(self.status_label, "error")
        layout.addWidget(self.status_label)

        # 1. 选择蛋白 PDB
        prot_card = StepCard(1, tr("选择蛋白 PDB"), layout_kind="vbox")
        prot_layout = QHBoxLayout()
        self.protein_input = QLineEdit()
        self.protein_input.setPlaceholderText(tr("选择蛋白 .pdb 文件..."))
        btn_browse_protein = QPushButton(tr("浏览..."))
        btn_browse_protein.clicked.connect(self.browse_protein)
        prot_layout.addWidget(self.protein_input)
        prot_layout.addWidget(btn_browse_protein)
        prot_card.content_layout.addLayout(prot_layout)
        layout.addWidget(prot_card)

        # 2. pdb2gmx
        pdb_card = StepCard(2, tr("处理受体蛋白 (pdb2gmx)"))
        pdb_layout = pdb_card.content_layout

        self.ff_combo = QComboBox()
        self.ff_combo.addItems(discover_forcefields())
        self.ff_combo.setCurrentText("oplsaa")
        pdb_layout.addRow(tr("力场 (-ff):"), self.ff_combo)

        self.water_combo = QComboBox()
        self.water_combo.addItems(["spce", "tip3p", "tip4p", "tip5p"])
        self.water_combo.setCurrentText("spce")
        pdb_layout.addRow(tr("水模型 (-water):"), self.water_combo)

        self.ignh_check = QCheckBox(tr("忽略输入文件中的氢原子 (-ignh)"))
        self.ignh_check.setChecked(True)
        pdb_layout.addRow("", self.ignh_check)

        btn_run_pdb2gmx = QPushButton(tr("运行 pdb2gmx"))
        btn_run_pdb2gmx.clicked.connect(self.run_pdb2gmx)
        set_role(btn_run_pdb2gmx, "primary")
        pdb_layout.addRow("", btn_run_pdb2gmx)

        layout.addWidget(pdb_card)

        # 3. 构建复合物
        build_card = StepCard(3, tr("构建复合物"), layout_kind="vbox")
        build_layout = build_card.content_layout
        
        build_info = QLabel(tr("合并 protein.gro + ligand.gro，更新 topol.top 加入配体拓扑。\n配体坐标应已处于正确空间位置（来自对接、实验结构等）。"))
        set_role(build_info, "hint-italic")
        build_layout.addWidget(build_info)
        
        btn_build_complex = QPushButton(tr("合并生成复合物 (complex.gro & topol.top)"))
        btn_build_complex.clicked.connect(self.build_complex)
        set_role(btn_build_complex, "primary")
        build_layout.addWidget(btn_build_complex)
        
        layout.addWidget(build_card)

        # 4. 溶剂化
        box_card = StepCard(4, tr("定义盒子与溶剂化"))
        box_layout = box_card.content_layout

        self.box_type = QComboBox()
        self.box_type.addItems(["cubic", "triclinic", "dodecahedron", "octahedron"])
        self.box_type.setCurrentText("cubic")
        box_layout.addRow(tr("盒子形状 (-bt):"), self.box_type)

        self.box_dist = QLineEdit("1.0")
        box_layout.addRow(tr("边缘距离 (-d, nm):"), self.box_dist)

        btn_run_box_solv = QPushButton(tr("运行 editconf & solvate"))
        btn_run_box_solv.clicked.connect(self.run_box_solv)
        set_role(btn_run_box_solv, "primary")
        box_layout.addRow("", btn_run_box_solv)

        layout.addWidget(box_card)

        # 5. 加离子
        genion_card = StepCard(5, tr("中和系统电荷 (genion)"))
        genion_layout = genion_card.content_layout
        
        genion_info = QLabel(tr("将自动运行 grompp 生成 ions.tpr，并使用 genion 替换水分子添加离子。"))
        genion_layout.addRow(genion_info)

        self.conc_input = QLineEdit("0.15")
        genion_layout.addRow(tr("盐浓度 (-conc, mol/L):"), self.conc_input)

        self.pname_input = QLineEdit("NA")
        genion_layout.addRow(tr("阳离子名称 (-pname):"), self.pname_input)

        self.nname_input = QLineEdit("CL")
        genion_layout.addRow(tr("阴离子名称 (-nname):"), self.nname_input)
        
        self.neutral_check = QCheckBox(tr("中和系统净电荷 (-neutral)"))
        self.neutral_check.setChecked(True)
        genion_layout.addRow("", self.neutral_check)

        btn_run_genion = QPushButton(tr("运行 grompp & genion"))
        btn_run_genion.clicked.connect(self.run_genion)
        set_role(btn_run_genion, "primary")
        genion_layout.addRow("", btn_run_genion)
        
        layout.addWidget(genion_card)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    # ------------------------------------------------------------------
    # 信号接收
    # ------------------------------------------------------------------
    def update_ligand_info(self, cwd, itp_path, gro_path):
        self.cwd = cwd
        self.ligand_itp = os.path.basename(itp_path)
        self.ligand_gro = os.path.basename(gro_path)
        self.status_label.setText(trf("✅ 配体: {itp} + {gro} (目录: {dir})", itp=self.ligand_itp, gro=self.ligand_gro, dir=self.cwd))
        set_role(self.status_label, "ok")

    def set_buttons_enabled(self, enabled):
        for child in self.findChildren(QPushButton):
            child.setEnabled(enabled)

    def get_ligand_molecule_name(self, itp_path):
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
        except:
            pass
        return "LIG"

    # ------------------------------------------------------------------
    # 浏览蛋白 PDB
    # ------------------------------------------------------------------
    def browse_protein(self):
        if not self.cwd:
            QMessageBox.warning(self, tr("警告"), tr("请先在「1. 配体准备」标签页中导入配体文件！"))
            return
        f, _ = QFileDialog.getOpenFileName(self, tr("选择蛋白 PDB 文件"), self.cwd, tr("PDB Files (*.pdb)"))
        if f:
            target_path = os.path.join(self.cwd, os.path.basename(f))
            if os.path.abspath(f) != os.path.abspath(target_path):
                shutil.copy(f, target_path)
            self.protein_input.setText(os.path.basename(f))

    # ------------------------------------------------------------------
    # pdb2gmx
    # ------------------------------------------------------------------
    def run_pdb2gmx(self):
        pdb_filename = self.protein_input.text()
        if not pdb_filename or not self.cwd:
            QMessageBox.warning(self, tr("警告"), tr("请先选择蛋白 PDB 文件。"))
            return

        protein_pdb = os.path.join(self.cwd, pdb_filename)
        if not os.path.exists(protein_pdb):
            QMessageBox.warning(self, tr("警告"), trf("未找到文件: {path}", path=protein_pdb))
            return

        # 自动去除 PDB 中 pdb2gmx 不认识的水分子和离子
        removed = strip_pdb_nonprotein(protein_pdb)
        if removed > 0:
            self.main_window.log(trf(">>> 自动清理: 从 PDB 中移除了 {n} 个非蛋白残基（水/离子）", n=removed))

        ff = self.ff_combo.currentText()
        water = self.water_combo.currentText()
        ignh = self.ignh_check.isChecked()

        args = ["pdb2gmx", "-f", pdb_filename, "-o", "protein.gro", "-p", "topol.top", "-ff", ff, "-water", water, "-ter"]
        if ignh:
            args.append("-ignh")

        self.worker_pdb2gmx = self.runner.create_worker(args, cwd=self.cwd, input_text="1\n0\n")
        self.worker_pdb2gmx.output_signal.connect(self.main_window.log)
        self.worker_pdb2gmx.finished_signal.connect(self.on_pdb2gmx_finished)
        
        self.set_buttons_enabled(False)
        self.worker_pdb2gmx.start()

    def on_pdb2gmx_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, tr("成功"), tr("pdb2gmx 运行成功，已生成 protein.gro 和 topol.top"))
        else:
            QMessageBox.critical(self, tr("错误"), trf("pdb2gmx 失败:\n{msg}", msg=message))

    # ------------------------------------------------------------------
    # 构建复合物
    # ------------------------------------------------------------------
    def build_complex(self):
        if not self.cwd or not self.ligand_itp or not self.ligand_gro:
            QMessageBox.warning(self, tr("警告"), tr("配体信息缺失！请先完成「1. 配体准备」。"))
            return
            
        prot_gro = os.path.join(self.cwd, "protein.gro")
        lig_gro = os.path.join(self.cwd, self.ligand_gro)
        comp_gro = os.path.join(self.cwd, "complex.gro")
        top_file = os.path.join(self.cwd, "topol.top")
        lig_itp_path = os.path.join(self.cwd, self.ligand_itp)
        
        if not os.path.exists(prot_gro) or not os.path.exists(top_file):
            QMessageBox.warning(self, tr("警告"), tr("未找到 protein.gro 或 topol.top，请先运行 pdb2gmx！"))
            return
        
        if not os.path.exists(lig_gro):
            QMessageBox.warning(self, tr("警告"), trf("未找到配体结构文件: {file}", file=lig_gro))
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
                    
            # 在 [ molecules ] 中按坐标顺序插入配体（蛋白后、溶剂前）
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
                
            QMessageBox.information(self, tr("成功"), trf("复合物构建成功！\n已生成 complex.gro\n已更新 topol.top (添加了 {name})", name=lig_name))
            
        except Exception as e:
            QMessageBox.critical(self, tr("错误"), trf("构建复合物时出错: {err}", err=str(e)))

    # ------------------------------------------------------------------
    # 溶剂化
    # ------------------------------------------------------------------
    def run_box_solv(self):
        if not self.cwd: return
        bt = self.box_type.currentText()
        d = self.box_dist.text()
        
        args_editconf = ["editconf", "-f", "complex.gro", "-o", "complex_newbox.gro", "-c", "-d", d, "-bt", bt]
        self.main_window.log("\n" + trf(">>> 运行 editconf: {cmd}", cmd=' '.join(args_editconf)))
        
        self.worker_editconf = self.runner.create_worker(args_editconf, cwd=self.cwd)
        self.worker_editconf.output_signal.connect(self.main_window.log)
        self.worker_editconf.finished_signal.connect(self.on_editconf_finished)
        
        self.set_buttons_enabled(False)
        self.worker_editconf.start()

    def on_editconf_finished(self, success, message):
        if not success:
            self.set_buttons_enabled(True)
            QMessageBox.critical(self, tr("错误"), trf("editconf 失败:\n{msg}", msg=message))
            return
            
        from core.config import get_solvent_template
        solvent = get_solvent_template(self.water_combo.currentText())
        self.main_window.log(trf("[溶剂化] 水模型: {model}, 溶剂模板: {tmpl}", model=self.water_combo.currentText(), tmpl=solvent))
        args_solvate = ["solvate", "-cp", "complex_newbox.gro", "-cs", solvent, "-o", "complex_solv.gro", "-p", "topol.top"]
        self.main_window.log("\n" + trf(">>> 运行 solvate: {cmd}", cmd=' '.join(args_solvate)))
        
        self.worker_solvate = self.runner.create_worker(args_solvate, cwd=self.cwd)
        self.worker_solvate.output_signal.connect(self.main_window.log)
        self.worker_solvate.finished_signal.connect(self.on_solvate_finished)
        self.worker_solvate.start()

    def on_solvate_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, tr("成功"), tr("已完成定义盒子与溶剂化，生成 complex_solv.gro"))
        else:
            QMessageBox.critical(self, tr("错误"), trf("solvate 失败:\n{msg}", msg=message))

    # ------------------------------------------------------------------
    # 加离子
    # ------------------------------------------------------------------
    def run_genion(self):
        if not self.cwd: return
        
        ions_mdp_path = os.path.join(self.cwd, "ions.mdp")
        with open(ions_mdp_path, "w") as f:
            f.write("; ions.mdp\n")
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
        
        self.main_window.log("\n" + trf(">>> 运行 grompp (为 genion 准备): {cmd}", cmd=' '.join(args_grompp)))
        self.worker_grompp = self.runner.create_worker(args_grompp, cwd=self.cwd)
        self.worker_grompp.output_signal.connect(self.main_window.log)
        self.worker_grompp.finished_signal.connect(self.on_genion_grompp_finished)
        
        self.set_buttons_enabled(False)
        self.worker_grompp.start()

    def on_genion_grompp_finished(self, success, message):
        if not success:
            self.set_buttons_enabled(True)
            QMessageBox.critical(self, tr("错误"), trf("grompp (ions) 失败:\n{msg}", msg=message))
            return
            
        conc = self.conc_input.text()
        pname = self.pname_input.text()
        nname = self.nname_input.text()
        
        args_genion = ["genion", "-s", "ions.tpr", "-o", "complex_solv_ions.gro", "-p", "topol.top", "-pname", pname, "-nname", nname]
        if self.neutral_check.isChecked():
            args_genion.append("-neutral")
        if conc:
            args_genion.extend(["-conc", conc])
            
        self.main_window.log("\n" + trf(">>> 运行 genion: {cmd}", cmd=' '.join(args_genion)))
        
        self.worker_genion = self.runner.create_worker(args_genion, cwd=self.cwd, input_text="SOL\n")
        self.worker_genion.output_signal.connect(self.main_window.log)
        self.worker_genion.finished_signal.connect(self.on_genion_finished)
        self.worker_genion.start()

    def on_genion_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, tr("成功"), tr("离子添加成功，生成 complex_solv_ions.gro\n复合物系统准备完毕。"))
        else:
            QMessageBox.critical(self, tr("错误"), trf("genion 失败:\n{msg}", msg=message))
