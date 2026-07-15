from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QLineEdit, 
                             QMessageBox, QFileDialog)
from PyQt6.QtCore import pyqtSignal
import os

class LigandPrepTab(QWidget):
    # 信号：当配体拓扑导入成功时发出，携带 cwd, itp_path
    topology_ready = pyqtSignal(str, str)

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
        
        # === 2. 导入配体拓扑 ===
        source_group = QGroupBox("2. 导入配体拓扑 (.itp)")
        source_layout = QVBoxLayout()
        
        # 提示：配体参数从哪来
        info_label = QLabel(
            "配体 .itp 文件需由外部工具生成，请通过以下任一方式获取：\n"
            "  - CGenFF (https://cgenff.silcsbio.com/)  上传配体 mol2/sdf → 下载 .str → 转为 .itp\n"
            "  - ATB (https://atb.uq.edu.au/)  上传配体结构 → 直接下载 GROMACS .itp\n"
            "  - LigParGen (http://zarbi.chem.yale.edu/ligpargen/)  OPLS-AA 参数\n"
            "  - PyRED / ACPYPE Server  生成 Amber GAFF → 转为 GROMACS 格式"
        )
        info_label.setStyleSheet("color: #555; font-size: 14px;")
        info_label.setWordWrap(True)
        source_layout.addWidget(info_label)
        
        import_layout = QFormLayout()
        
        self.itp_input = QLineEdit()
        btn_browse_itp = QPushButton("浏览 .itp")
        btn_browse_itp.clicked.connect(lambda: self.browse_file(self.itp_input, "GROMACS Topology (*.itp)"))
        import_layout.addRow("拓扑文件 (.itp):", self.create_browse_row(self.itp_input, btn_browse_itp))
        
        btn_confirm_import = QPushButton("确认导入")
        btn_confirm_import.clicked.connect(self.confirm_import)
        import_layout.addRow("", btn_confirm_import)
        
        source_layout.addLayout(import_layout)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        # === 3. 结果预览 ===
        res_group = QGroupBox("3. 结果预览")
        res_layout = QVBoxLayout()
        self.res_info = QLabel("尚未导入配体拓扑。")
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
        
        if not itp_filename:
            QMessageBox.warning(self, "警告", "请提供 .itp 文件")
            return
            
        full_itp_path = os.path.join(self.cwd, itp_filename)
            
        if not os.path.exists(full_itp_path):
            QMessageBox.warning(self, "警告", "文件不存在于工作目录中，请重新选择")
            return
            
        # 标准化文件名为 ligand.itp
        try:
            import shutil
            target_itp = os.path.join(self.cwd, "ligand.itp")
            if os.path.abspath(full_itp_path) != os.path.abspath(target_itp):
                shutil.copy(full_itp_path, target_itp)
            
            self.res_info.setText(
                f"✅ 配体拓扑已就绪！\n"
                f"拓扑文件: {target_itp}\n\n"
                f"下一步：请在「复合物拓扑与水箱」标签页中选择复合物 PDB 文件。"
            )
            self.res_info.setStyleSheet("color: green; font-weight: bold;")
            self.topology_ready.emit(self.cwd, target_itp)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
