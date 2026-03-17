from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QFormLayout, QLabel, QLineEdit, 
                             QComboBox, QPushButton, QScrollArea, QWidget, QGroupBox)
from PyQt6.QtCore import Qt

class MDPEditor(QDialog):
    def __init__(self, parent=None, mdp_type="nvt", current_content=""):
        super().__init__(parent)
        self.setWindowTitle(f"MDP 参数配置 - {mdp_type.upper()}")
        self.resize(600, 700)
        self.mdp_type = mdp_type
        self.params = {}
        
        # 解析当前的 MDP 内容
        self.parse_mdp(current_content)
        
        self.init_ui()
        
    def parse_mdp(self, content):
        """简单的 MDP 解析器"""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith(';'):
                continue
            
            # 去除行尾注释
            if ';' in line:
                line = line.split(';')[0].strip()
                
            if '=' in line:
                key, value = line.split('=', 1)
                self.params[key.strip()] = value.strip()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.form_layout = QFormLayout(content_widget)
        
        # === 1. 运行控制 ===
        self.add_section_header("运行控制 (Run Control)")
        if self.mdp_type == "em":
            self.integrator = self.add_combo_param("integrator", ["steep", "cg"], "积分算法")
            self.nsteps = self.add_line_param("nsteps", "50000", "最大步数")
            self.emtol = self.add_line_param("emtol", "1000.0", "能量最小化容差 (kJ/mol/nm)")
            self.emstep = self.add_line_param("emstep", "0.01", "初始步长 (nm)")
        else:
            self.integrator = self.add_combo_param("integrator", ["md", "steep", "cg"], "积分算法")
            self.nsteps = self.add_line_param("nsteps", "50000", "总步数")
            self.dt = self.add_line_param("dt", "0.002", "时间步长 (ps)")
        
        # === 2. 输出控制 ===
        self.add_section_header("输出控制 (Output Control)")
        self.nstxout = self.add_line_param("nstxout", "500", "坐标输出频率 (步)")
        self.nstvout = self.add_line_param("nstvout", "500", "速度输出频率 (步)")
        self.nstfout = self.add_line_param("nstfout", "0", "力输出频率 (步)")
        self.nstenergy = self.add_line_param("nstenergy", "500", "能量输出频率 (步)")
        self.nstlog = self.add_line_param("nstlog", "500", "日志输出频率 (步)")
        
        if self.mdp_type == "md":
            self.nstxout_compressed = self.add_line_param("nstxout-compressed", "5000", "压缩坐标输出频率 (步)")
            self.compressed_x_grps = self.add_line_param("compressed-x-grps", "System", "压缩坐标组")
        
        # === 3. 邻居搜索与相互作用 ===
        self.add_section_header("邻居搜索与相互作用 (Neighbor Searching)")
        self.cutoff_scheme = self.add_combo_param("cutoff-scheme", ["Verlet", "group"], "Cutoff 方案")
        self.ns_type = self.add_combo_param("ns_type", ["grid", "simple"], "搜索类型")
        self.nstlist = self.add_line_param("nstlist", "10", "更新频率")
        self.coulombtype = self.add_combo_param("coulombtype", ["PME", "Cut-off", "Reaction-Field"], "静电相互作用")
        self.rcoulomb = self.add_line_param("rcoulomb", "1.0", "静电 Cutoff (nm)")
        self.rvdw = self.add_line_param("rvdw", "1.0", "范德华 Cutoff (nm)")
        
        # === 4. 温度耦合 ===
        if self.mdp_type not in ["em"]:
            self.add_section_header("温度耦合 (Temperature Coupling)")
            self.tcoupl = self.add_combo_param("tcoupl", ["no", "berendsen", "v-rescale", "nose-hoover"], "控温算法")
            self.tc_grps = self.add_line_param("tc-grps", "Protein Non-Protein", "耦合组")
            self.tau_t = self.add_line_param("tau_t", "0.1 0.1", "耦合时间常数 (ps)")
            self.ref_t = self.add_line_param("ref_t", "300 300", "参考温度 (K)")
        
        # === 5. 压力耦合 (仅 NPT/MD) ===
        if self.mdp_type in ["npt", "md"]:
            self.add_section_header("压力耦合 (Pressure Coupling)")
            self.pcoupl = self.add_combo_param("pcoupl", ["no", "berendsen", "parrinello-rahman", "c-rescale"], "控压算法")
            self.pcoupltype = self.add_combo_param("pcoupltype", ["isotropic", "semiisotropic", "anisotropic"], "耦合类型")
            self.tau_p = self.add_line_param("tau_p", "2.0", "耦合时间常数 (ps)")
            self.ref_p = self.add_line_param("ref_p", "1.0", "参考压力 (bar)")
            self.compressibility = self.add_line_param("compressibility", "4.5e-5", "压缩系数")
            
        # === 6. 其他 ===
        self.add_section_header("其他设置 (Others)")
        self.pbc = self.add_combo_param("pbc", ["xyz", "no", "xy"], "周期性边界条件")
        self.constraints = self.add_combo_param("constraints", ["none", "h-bonds", "all-bonds"], "键长约束")
        self.continuation = self.add_combo_param("continuation", ["yes", "no"], "是否延续运行")
        
        if self.mdp_type == "nvt":
            self.gen_vel = self.add_combo_param("gen_vel", ["yes", "no"], "生成初始速度")
            self.gen_temp = self.add_line_param("gen_temp", "300", "初始速度温度 (K)")
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("生成 MDP 内容")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        main_layout.addLayout(btn_layout)
        
    def add_section_header(self, title):
        label = QLabel(title)
        label.setStyleSheet("font-weight: bold; color: #4a90e2; margin-top: 10px; margin-bottom: 5px;")
        self.form_layout.addRow(label)
        
    def add_line_param(self, key, default, label_text):
        value = self.params.get(key, default)
        widget = QLineEdit(value)
        self.form_layout.addRow(f"{label_text} ({key}):", widget)
        # 存储引用以便后续获取值
        setattr(self, f"widget_{key}", widget)
        return widget

    def add_combo_param(self, key, options, label_text):
        value = self.params.get(key, options[0])
        widget = QComboBox()
        widget.addItems(options)
        if value in options:
            widget.setCurrentText(value)
        else:
            # 如果现有值不在选项中，添加它
            widget.addItem(value)
            widget.setCurrentText(value)
            
        self.form_layout.addRow(f"{label_text} ({key}):", widget)
        setattr(self, f"widget_{key}", widget)
        return widget
        
    def get_mdp_content(self):
        """生成格式化的 MDP 内容"""
        content = f"; Generated by GROMACS-GUI MDP Editor\n"
        content += f"; Type: {self.mdp_type.upper()}\n\n"
        
        # 遍历所有已知的 key 生成内容
        keys = [
            "integrator", "nsteps", "dt", "emtol", "emstep",
            "nstxout", "nstvout", "nstfout", "nstenergy", "nstlog",
            "nstxout-compressed", "compressed-x-grps",
            "cutoff-scheme", "ns_type", "nstlist", "coulombtype", "rcoulomb", "rvdw",
            "tcoupl", "tc-grps", "tau_t", "ref_t",
            "pcoupl", "pcoupltype", "tau_p", "ref_p", "compressibility",
            "pbc", "constraints", "continuation", "gen_vel", "gen_temp"
        ]
        
        for key in keys:
            if hasattr(self, f"widget_{key}"):
                widget = getattr(self, f"widget_{key}")
                if isinstance(widget, QLineEdit):
                    val = widget.text()
                elif isinstance(widget, QComboBox):
                    val = widget.currentText()
                else:
                    continue
                
                # 对齐格式
                content += f"{key:<25} = {val}\n"
                
        # 添加一些可能未在 GUI 中显示但存在于原内容中的参数（如果需要保留）
        # 这里简化处理，只生成标准参数
        
        return content
