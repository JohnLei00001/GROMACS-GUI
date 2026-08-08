from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QFormLayout, QLabel, QLineEdit, 
                             QComboBox, QPushButton, QScrollArea, QWidget)
from PyQt6.QtCore import Qt
from gui.i18n import tr, trf
from gui.theme import set_role

class MDPEditor(QDialog):
    def __init__(self, parent=None, mdp_type="nvt", current_content=""):
        super().__init__(parent)
        self.setWindowTitle(trf("MDP 参数配置 - {type}", type=mdp_type.upper()))
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
        self.add_section_header(tr("运行控制 (Run Control)"))
        if self.mdp_type == "em":
            self.integrator = self.add_combo_param("integrator", ["steep", "cg"], tr("积分算法"))
            self.nsteps = self.add_line_param("nsteps", "50000", tr("最大步数"))
            self.emtol = self.add_line_param("emtol", "1000.0", tr("能量最小化容差 (kJ/mol/nm)"))
            self.emstep = self.add_line_param("emstep", "0.01", tr("初始步长 (nm)"))
        else:
            self.integrator = self.add_combo_param("integrator", ["md", "steep", "cg"], tr("积分算法"))
            self.nsteps = self.add_line_param("nsteps", "50000", tr("总步数"))
            self.dt = self.add_line_param("dt", "0.002", tr("时间步长 (ps)"))
        
        # === 2. 输出控制 ===
        self.add_section_header(tr("输出控制 (Output Control)"))
        self.nstxout = self.add_line_param("nstxout", "500", tr("坐标输出频率 (步)"))
        self.nstvout = self.add_line_param("nstvout", "500", tr("速度输出频率 (步)"))
        self.nstfout = self.add_line_param("nstfout", "0", tr("力输出频率 (步)"))
        self.nstenergy = self.add_line_param("nstenergy", "500", tr("能量输出频率 (步)"))
        self.nstlog = self.add_line_param("nstlog", "500", tr("日志输出频率 (步)"))
        
        if self.mdp_type == "md":
            self.nstxout_compressed = self.add_line_param("nstxout-compressed", "5000", tr("压缩坐标输出频率 (步)"))
            self.compressed_x_grps = self.add_line_param("compressed-x-grps", "System", tr("压缩坐标组"))
        
        # === 3. 邻居搜索与相互作用 ===
        self.add_section_header(tr("邻居搜索与相互作用 (Neighbor Searching)"))
        self.cutoff_scheme = self.add_combo_param("cutoff-scheme", ["Verlet", "group"], tr("Cutoff 方案"))
        self.ns_type = self.add_combo_param("ns_type", ["grid", "simple"], tr("搜索类型"))
        self.nstlist = self.add_line_param("nstlist", "10", tr("更新频率"))
        self.coulombtype = self.add_combo_param("coulombtype", ["PME", "Cut-off", "Reaction-Field"], tr("静电相互作用"))
        self.rcoulomb = self.add_line_param("rcoulomb", "1.0", tr("静电 Cutoff (nm)"))
        self.rvdw = self.add_line_param("rvdw", "1.0", tr("范德华 Cutoff (nm)"))
        
        # === 4. 温度耦合 ===
        if self.mdp_type not in ["em"]:
            self.add_section_header(tr("温度耦合 (Temperature Coupling)"))
            self.tcoupl = self.add_combo_param("tcoupl", ["no", "berendsen", "v-rescale", "nose-hoover"], tr("控温算法"))
            self.tc_grps = self.add_line_param("tc-grps", "Protein Non-Protein", tr("耦合组"))
            self.tau_t = self.add_line_param("tau_t", "0.1 0.1", tr("耦合时间常数 (ps)"))
            self.ref_t = self.add_line_param("ref_t", "300 300", tr("参考温度 (K)"))
        
        # === 5. 压力耦合 (仅 NPT/MD) ===
        if self.mdp_type in ["npt", "md"]:
            self.add_section_header(tr("压力耦合 (Pressure Coupling)"))
            self.pcoupl = self.add_combo_param("pcoupl", ["no", "berendsen", "parrinello-rahman", "c-rescale"], tr("控压算法"))
            self.pcoupltype = self.add_combo_param("pcoupltype", ["isotropic", "semiisotropic", "anisotropic"], tr("耦合类型"))
            self.tau_p = self.add_line_param("tau_p", "2.0", tr("耦合时间常数 (ps)"))
            self.ref_p = self.add_line_param("ref_p", "1.0", tr("参考压力 (bar)"))
            self.compressibility = self.add_line_param("compressibility", "4.5e-5", tr("压缩系数"))
            
        # === 6. 其他 ===
        self.add_section_header(tr("其他设置 (Others)"))
        self.pbc = self.add_combo_param("pbc", ["xyz", "no", "xy"], tr("周期性边界条件"))
        self.constraints = self.add_combo_param("constraints", ["none", "h-bonds", "all-bonds"], tr("键长约束"))
        self.continuation = self.add_combo_param("continuation", ["yes", "no"], tr("是否延续运行"))
        
        if self.mdp_type == "nvt":
            self.gen_vel = self.add_combo_param("gen_vel", ["yes", "no"], tr("生成初始速度"))
            self.gen_temp = self.add_line_param("gen_temp", "300", tr("初始速度温度 (K)"))
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_save = QPushButton(tr("生成 MDP 内容"))
        btn_save.clicked.connect(self.accept)
        set_role(btn_save, "primary")
        btn_cancel = QPushButton(tr("取消"))
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        main_layout.addLayout(btn_layout)
        
    def add_section_header(self, title):
        label = QLabel(title)
        set_role(label, "section")
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
        """生成格式化的 MDP 内容，保留原始文件中 GUI 未覆盖的参数"""
        content = f"; Generated by GROMACS-GUI MDP Editor\n"
        content += f"; Type: {self.mdp_type.upper()}\n\n"
        
        # 所有 GUI 已知的参数 key
        gui_keys = [
            "integrator", "nsteps", "dt", "emtol", "emstep",
            "nstxout", "nstvout", "nstfout", "nstenergy", "nstlog",
            "nstxout-compressed", "compressed-x-grps",
            "cutoff-scheme", "ns_type", "nstlist", "coulombtype", "rcoulomb", "rvdw",
            "tcoupl", "tc-grps", "tau_t", "ref_t",
            "pcoupl", "pcoupltype", "tau_p", "ref_p", "compressibility",
            "pbc", "constraints", "continuation", "gen_vel", "gen_temp"
        ]
        
        # 1. 先输出 GUI 中的参数（值可能已被用户修改）
        output_keys = set()
        for key in gui_keys:
            if hasattr(self, f"widget_{key}"):
                widget = getattr(self, f"widget_{key}")
                if isinstance(widget, QLineEdit):
                    val = widget.text()
                elif isinstance(widget, QComboBox):
                    val = widget.currentText()
                else:
                    continue
                content += f"{key:<25} = {val}\n"
                output_keys.add(key)
        
        # 2. 追加原始 MDP 中存在但 GUI 没有对应控件的参数（保留原值不丢失）
        extra_keys = [k for k in self.params if k not in output_keys]
        if extra_keys:
            content += "\n; 以下为原始 MDP 中保留的其他参数\n"
            for key in extra_keys:
                content += f"{key:<25} = {self.params[key]}\n"
        
        return content
