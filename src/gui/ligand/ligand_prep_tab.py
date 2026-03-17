from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QComboBox, QLineEdit, 
                             QMessageBox, QFileDialog, QRadioButton, QButtonGroup, QTextEdit)
from PyQt6.QtCore import pyqtSignal
import os
import shutil

class LigandPrepTab(QWidget):
    # 信号：当拓扑生成或导入成功时发出，携带 cwd, itp_path, gro_path
    topology_ready = pyqtSignal(str, str, str)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.cwd = os.getcwd() # 默认当前目录，实际应由用户选择工作目录
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # === 1. 工作目录 ===
        dir_group = QGroupBox("1. 设置工作目录")
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit(self.cwd)
        btn_browse_dir = QPushButton("浏览...")
        btn_browse_dir.clicked.connect(self.browse_dir)
        dir_layout.addWidget(QLabel("目录:"))
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(btn_browse_dir)
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)
        
        # === 2. 配体拓扑来源 ===
        source_group = QGroupBox("2. 配体拓扑来源")
        source_layout = QVBoxLayout()
        
        self.mode_group = QButtonGroup(self)
        self.rb_import = QRadioButton("导入现有拓扑 (.itp + .gro/.pdb)")
        self.rb_generate = QRadioButton("自动生成拓扑 (使用 ACPYPE/OpenBabel)")
        self.rb_import.setChecked(True) # 默认导入，因为生成需要环境支持
        self.mode_group.addButton(self.rb_import)
        self.mode_group.addButton(self.rb_generate)
        
        source_layout.addWidget(self.rb_import)
        source_layout.addWidget(self.rb_generate)
        
        # --- 导入面板 ---
        self.import_widget = QWidget()
        import_layout = QFormLayout(self.import_widget)
        
        self.itp_input = QLineEdit()
        btn_browse_itp = QPushButton("浏览 .itp")
        btn_browse_itp.clicked.connect(lambda: self.browse_file(self.itp_input, "GROMACS Topology (*.itp)"))
        
        self.gro_input = QLineEdit()
        btn_browse_gro = QPushButton("浏览 .gro/.pdb")
        btn_browse_gro.clicked.connect(lambda: self.browse_file(self.gro_input, "Structure Files (*.gro *.pdb)"))
        
        import_layout.addRow("拓扑文件 (.itp):", self.create_browse_row(self.itp_input, btn_browse_itp))
        import_layout.addRow("结构文件 (.gro/.pdb):", self.create_browse_row(self.gro_input, btn_browse_gro))
        
        btn_confirm_import = QPushButton("确认导入")
        btn_confirm_import.clicked.connect(self.confirm_import)
        import_layout.addRow("", btn_confirm_import)
        
        source_layout.addWidget(self.import_widget)
        
        # --- 生成面板 ---
        self.gen_widget = QWidget()
        gen_layout = QFormLayout(self.gen_widget)
        
        self.mol_input = QLineEdit()
        btn_browse_mol = QPushButton("浏览 .mol2/.sdf")
        btn_browse_mol.clicked.connect(lambda: self.browse_file(self.mol_input, "Small Molecule (*.mol2 *.sdf *.pdb)"))
        
        self.charge_input = QLineEdit("0")
        self.multiplicity_input = QLineEdit("1")
        self.atom_type_combo = QComboBox()
        self.atom_type_combo.addItems(["gaff", "gaff2", "amber"])
        
        gen_layout.addRow("小分子文件:", self.create_browse_row(self.mol_input, btn_browse_mol))
        gen_layout.addRow("净电荷 (Net Charge):", self.charge_input)
        gen_layout.addRow("自旋多重度 (Multiplicity):", self.multiplicity_input)
        gen_layout.addRow("原子类型 (Atom Type):", self.atom_type_combo)
        
        btn_run_acpype = QPushButton("运行 ACPYPE 生成拓扑")
        btn_run_acpype.clicked.connect(self.run_acpype)
        gen_layout.addRow("", btn_run_acpype)
        
        self.gen_widget.setVisible(False)
        source_layout.addWidget(self.gen_widget)
        
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        # === 3. 结果预览 ===
        res_group = QGroupBox("3. 结果预览")
        res_layout = QVBoxLayout()
        self.res_info = QLabel("尚未加载配体拓扑。")
        self.res_info.setWordWrap(True)
        res_layout.addWidget(self.res_info)
        res_group.setLayout(res_layout)
        layout.addWidget(res_group)

        layout.addStretch()

        # 连接单选框切换事件
        self.rb_import.toggled.connect(self.toggle_mode)
        self.rb_generate.toggled.connect(self.toggle_mode)

    def create_browse_row(self, line_edit, button):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0,0,0,0)
        l.addWidget(line_edit)
        l.addWidget(button)
        return w

    def toggle_mode(self):
        is_import = self.rb_import.isChecked()
        self.import_widget.setVisible(is_import)
        self.gen_widget.setVisible(not is_import)

    def browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择工作目录", self.cwd)
        if d:
            self.cwd = d
            self.dir_input.setText(d)

    def browse_file(self, line_edit, filter_str):
        f, _ = QFileDialog.getOpenFileName(self, "选择文件", self.cwd, filter_str)
        if f:
            line_edit.setText(f)

    def confirm_import(self):
        itp = self.itp_input.text()
        gro = self.gro_input.text()
        
        if not itp or not gro:
            QMessageBox.warning(self, "警告", "请同时提供 .itp 和 .gro/.pdb 文件")
            return
            
        if not os.path.exists(itp) or not os.path.exists(gro):
            QMessageBox.warning(self, "警告", "文件不存在，请检查路径")
            return
            
        # 复制文件到工作目录
        try:
            target_itp = os.path.join(self.cwd, "ligand.itp")
            target_gro = os.path.join(self.cwd, "ligand.gro")
            
            # 如果是 pdb，尝试转换为 gro (这里简单复制，后面步骤处理)
            # 为了统一，我们尽量引导用户提供 gro，或者我们在这里调用 editconf 转一下
            
            shutil.copy(itp, target_itp)
            
            if gro.endswith('.pdb'):
                # 转换 pdb -> gro
                args = ["editconf", "-f", gro, "-o", "ligand.gro"]
                self.worker_convert = self.runner.create_worker(args, cwd=self.cwd)
                self.worker_convert.output_signal.connect(self.main_window.log)
                self.worker_convert.finished_signal.connect(lambda s, m: self.on_convert_finished(s, m, target_itp, target_gro))
                self.worker_convert.start()
            else:
                shutil.copy(gro, target_gro)
                self.finish_setup(target_itp, target_gro)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")

    def on_convert_finished(self, success, message, itp_path, gro_path):
        if success:
            self.finish_setup(itp_path, gro_path)
        else:
            QMessageBox.critical(self, "错误", f"PDB 转 GRO 失败: {message}")

    def run_acpype(self):
        mol = self.mol_input.text()
        if not mol or not os.path.exists(mol):
            QMessageBox.warning(self, "警告", "请选择有效的小分子文件")
            return
            
        # 检查 acpype 是否可用
        # 这里假设用户环境里有 acpype 命令
        # 我们可以尝试运行 acpype -h 来检查
        
        charge = self.charge_input.text()
        mult = self.multiplicity_input.text()
        atom_type = self.atom_type_combo.currentText()
        
        # 构造命令
        # acpype -i input.mol2 -c user -n charge -m mult -a atom_type
        args = ["acpype", "-i", mol, "-c", "user", "-n", charge, "-m", mult, "-a", atom_type]
        
        self.main_window.log(f"\n>>> 正在运行: {' '.join(args)}")
        
        self.worker_acpype = self.runner.create_worker(args, cwd=self.cwd)
        self.worker_acpype.output_signal.connect(self.main_window.log)
        self.worker_acpype.finished_signal.connect(self.on_acpype_finished)
        self.worker_acpype.start()
        
        # 禁用按钮防止重复点击
        self.gen_widget.setEnabled(False)

    def on_acpype_finished(self, success, message):
        self.gen_widget.setEnabled(True)
        if success:
            # ACPYPE 通常会生成一个以输入文件名命名的目录，或者直接在当前目录生成
            # 假设生成了 MOL_GMX.itp 和 MOL_GMX.gro (默认行为)
            # 或者根据输入文件名: input.acpype/input_GMX.itp
            
            # 我们需要查找生成的 .itp 和 .gro
            # 简单起见，遍历 cwd 找最新的 itp/gro
            
            # 提示用户检查输出
            QMessageBox.information(self, "成功", "ACPYPE 运行完成！请在导入面板中选择生成的 .itp 和 .gro 文件。")
            self.rb_import.setChecked(True) # 切换回导入模式让用户确认
        else:
            QMessageBox.critical(self, "错误", f"ACPYPE 运行失败: {message}\n请确保已安装 acpype (pip install acpype) 且相关依赖 (AmberTools/OpenBabel) 正常。")

    def finish_setup(self, itp_path, gro_path):
        self.res_info.setText(f"✅ 配体准备就绪！\n拓扑文件: {itp_path}\n结构文件: {gro_path}")
        self.res_info.setStyleSheet("color: green; font-weight: bold;")
        self.topology_ready.emit(self.cwd, itp_path, gro_path)
