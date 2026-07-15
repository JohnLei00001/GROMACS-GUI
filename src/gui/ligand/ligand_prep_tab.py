from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QLineEdit, 
                             QMessageBox, QFileDialog)
from PyQt6.QtCore import pyqtSignal
import os
import shutil

class LigandPrepTab(QWidget):
    # 信号：配体导入成功时发出 (cwd, itp_path, gro_path)
    topology_ready = pyqtSignal(str, str, str)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.cwd = ""
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # === 1. 工作目录 ===
        dir_group = QGroupBox("1. 设置工作目录")
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit(self.cwd)
        self.dir_input.setPlaceholderText("选择输入文件后将自动使用其所在目录")
        btn_browse_dir = QPushButton("浏览...")
        btn_browse_dir.clicked.connect(self.browse_dir)
        dir_layout.addWidget(QLabel("目录:"))
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(btn_browse_dir)
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)
        
        # === 2. 导入配体文件 ===
        source_group = QGroupBox("2. 导入配体文件")
        source_layout = QVBoxLayout()
        
        info_label = QLabel(
            "请提供外部工具（CGenFF、ATB、LigParGen 等）生成的配体拓扑和结构文件。\n"
            "拓扑 (.itp) 和结构 (.gro/.pdb) 必须来自同一来源，以保证原子数一致。\n"
            "配体坐标应已处于蛋白结合位点附近的正确参考系中（如来自对接、实验结构等）。"
        )
        info_label.setStyleSheet("color: #555; font-size: 14px;")
        info_label.setWordWrap(True)
        source_layout.addWidget(info_label)
        
        import_layout = QFormLayout()
        
        self.itp_input = QLineEdit()
        btn_browse_itp = QPushButton("浏览 .itp")
        btn_browse_itp.clicked.connect(lambda: self.browse_file(self.itp_input, "GROMACS Topology (*.itp *.itp)"))
        import_layout.addRow("拓扑文件 (.itp):", self.create_browse_row(self.itp_input, btn_browse_itp))
        
        self.gro_input = QLineEdit()
        btn_browse_gro = QPushButton("浏览 .gro/.pdb")
        btn_browse_gro.clicked.connect(lambda: self.browse_file(self.gro_input, "Structure Files (*.gro *.pdb)"))
        import_layout.addRow("结构文件 (.gro/.pdb):", self.create_browse_row(self.gro_input, btn_browse_gro))
        
        btn_confirm_import = QPushButton("确认导入")
        btn_confirm_import.clicked.connect(self.confirm_import)
        import_layout.addRow("", btn_confirm_import)
        
        source_layout.addLayout(import_layout)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        # === 3. 结果预览 ===
        res_group = QGroupBox("3. 结果预览")
        res_layout = QVBoxLayout()
        self.res_info = QLabel("尚未导入配体文件。")
        self.res_info.setWordWrap(True)
        res_layout.addWidget(self.res_info)
        res_group.setLayout(res_layout)
        layout.addWidget(res_group)

        layout.addStretch()

    def create_browse_row(self, line_edit, button):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0,0,0,0)
        l.addWidget(line_edit)
        l.addWidget(button)
        return w

    def browse_dir(self):
        start_dir = self.cwd or os.getcwd()
        d = QFileDialog.getExistingDirectory(self, "选择工作目录", start_dir)
        if d:
            self.cwd = d
            self.dir_input.setText(d)

    def browse_file(self, line_edit, filter_str):
        start_dir = self.cwd or os.getcwd()
        f, _ = QFileDialog.getOpenFileName(self, "选择文件", start_dir, filter_str)
        if f:
            self.cwd = os.path.dirname(f)
            file_name = os.path.basename(f)
            self.dir_input.setText(self.cwd)
            line_edit.setText(file_name)
            self.main_window.log(f"已选择文件: {file_name}")
            self.main_window.log(f"工作目录已切换为输入文件所在目录: {self.cwd}")

    def confirm_import(self):
        itp_filename = self.itp_input.text()
        gro_filename = self.gro_input.text()
        
        if not itp_filename or not gro_filename:
            QMessageBox.warning(self, "警告", "请同时提供 .itp 和 .gro/.pdb 文件")
            return
            
        full_itp_path = os.path.join(self.cwd, itp_filename)
        full_gro_path = os.path.join(self.cwd, gro_filename)
            
        if not os.path.exists(full_itp_path):
            QMessageBox.warning(self, "警告", "拓扑文件不存在于工作目录中，请重新选择")
            return
        if not os.path.exists(full_gro_path):
            QMessageBox.warning(self, "警告", "结构文件不存在于工作目录中，请重新选择")
            return
            
        try:
            # 标准化文件名为 ligand.itp / ligand.gro
            target_itp = os.path.join(self.cwd, "ligand.itp")
            if os.path.abspath(full_itp_path) != os.path.abspath(target_itp):
                shutil.copy(full_itp_path, target_itp)
            
            # 判断扩展名，统一为 .gro
            ext = os.path.splitext(gro_filename)[1].lower()
            if ext == '.pdb':
                target_gro = os.path.join(self.cwd, "ligand.pdb")
            else:
                target_gro = os.path.join(self.cwd, "ligand.gro")
            if os.path.abspath(full_gro_path) != os.path.abspath(target_gro):
                shutil.copy(full_gro_path, target_gro)
            
            self.res_info.setText(
                f"✅ 配体文件已就绪！\n"
                f"拓扑: {target_itp}\n"
                f"结构: {target_gro}\n\n"
                f"下一步：请在「复合物拓扑与水箱」标签页中选择蛋白 PDB 文件。"
            )
            self.res_info.setStyleSheet("color: green; font-weight: bold;")
            self.topology_ready.emit(self.cwd, target_itp, target_gro)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
