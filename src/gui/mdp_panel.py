from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel, QFormLayout, QFrame,
                             QComboBox, QLineEdit, QTextEdit, QToolButton)
from PyQt6.QtCore import Qt, pyqtSignal
from gui.i18n import tr
from gui.theme import set_role
import re

# ── default values per section ──────────────────────────────────────────────
_DEFAULTS = {
    "integrator":        "md",
    "nsteps":            "50000",
    "dt":                "0.002",
    "emtol":             "1000.0",
    "emstep":            "0.01",
    "nstxout":           "500",
    "nstvout":           "500",
    "nstfout":           "0",
    "nstenergy":         "500",
    "nstlog":            "500",
    "nstxout-compressed": "5000",
    "compressed-x-grps": "System",
    "cutoff-scheme":     "Verlet",
    "ns_type":           "grid",
    "nstlist":           "10",
    "coulombtype":       "PME",
    "rcoulomb":          "1.0",
    "rvdw":              "1.0",
    "DispCorr":          "no",
    "pme_order":         "4",
    "fourierspacing":    "0.16",
    "tcoupl":            "V-rescale",
    "tc-grps":           "System",
    "tau_t":             "0.1",
    "ref_t":             "300",
    "pcoupl":            "Parrinello-Rahman",
    "pcoupltype":        "isotropic",
    "tau_p":             "2.0",
    "ref_p":             "1.0",
    "compressibility":   "4.5e-5",
    "constraint_algorithm": "lincs",
    "constraints":       "h-bonds",
    "continuation":      "no",
    "gen_vel":           "yes",
    "gen_temp":          "300",
    "gen_seed":          "-1",
    "pbc":               "xyz",
}

_MDP_TYPE_SECTIONS = {
    "em":    ["run_em", "neighbor", "electrostatics", "pbc"],
    "nvt":   ["run", "output", "neighbor", "electrostatics", "thermostat", "constraints", "velocity", "pbc"],
    "npt":   ["run", "output", "neighbor", "electrostatics", "thermostat", "barostat", "constraints", "pbc"],
    "md":    ["run", "output_md", "neighbor", "electrostatics", "thermostat", "barostat", "constraints", "continuation", "pbc"],
}

_SECTION_KEYS = {
    "run_em":        ["integrator", "nsteps", "emtol", "emstep"],
    "run":           ["integrator", "nsteps", "dt"],
    "output":        ["nstxout", "nstvout", "nstfout", "nstenergy", "nstlog"],
    "output_md":     ["nstxout", "nstvout", "nstfout", "nstenergy", "nstlog",
                      "nstxout-compressed", "compressed-x-grps"],
    "neighbor":      ["cutoff-scheme", "ns_type", "nstlist", "rcoulomb", "rvdw", "DispCorr"],
    "electrostatics":["coulombtype", "pme_order", "fourierspacing"],
    "thermostat":    ["tcoupl", "tc-grps", "tau_t", "ref_t"],
    "barostat":      ["pcoupl", "pcoupltype", "tau_p", "ref_p", "compressibility"],
    "constraints":   ["constraint_algorithm", "constraints"],
    "continuation":  ["continuation"],
    "velocity":      ["gen_vel", "gen_temp", "gen_seed"],
    "pbc":           ["pbc"],
}

_WIDGET_TYPE = {
    "integrator":                ("combo", ["steep","cg","md"]),
    "cutoff-scheme":             ("combo", ["Verlet","group"]),
    "ns_type":                   ("combo", ["grid","simple"]),
    "coulombtype":               ("combo", ["PME","Cut-off","Reaction-Field"]),
    "DispCorr":                  ("combo", ["no","EnerPres","Ener"]),
    "tcoupl":                    ("combo", ["no","berendsen","V-rescale","nose-hoover"]),
    "pcoupl":                    ("combo", ["no","berendsen","Parrinello-Rahman","C-rescale"]),
    "pcoupltype":                ("combo", ["isotropic","semiisotropic","anisotropic","surface-tension"]),
    "constraint_algorithm":       ("combo", ["lincs","shake","none"]),
    "constraints":               ("combo", ["none","h-bonds","all-bonds"]),
    "continuation":              ("combo", ["yes","no"]),
    "gen_vel":                   ("combo", ["yes","no"]),
    "pbc":                       ("combo", ["xyz","no","xy"]),
}

# 分区标题（中英对照）
_SECTION_TITLES = {
    "run_em":        "运行控制 (Run Control)",
    "run":           "运行控制 (Run Control)",
    "output":        "输出控制 (Output Control)",
    "output_md":     "输出控制 (Output Control)",
    "neighbor":      "邻居搜索与相互作用 (Neighbor Searching)",
    "electrostatics": "静电学 (Electrostatics)",
    "thermostat":    "温度耦合 (Temperature Coupling)",
    "barostat":      "压力耦合 (Pressure Coupling)",
    "constraints":   "键长约束 (Constraints)",
    "continuation":  "续跑设置 (Continuation)",
    "velocity":      "初始速度生成 (Velocity Generation)",
    "pbc":           "周期性边界条件 (PBC)",
}

# 默认展开的分区（核心参数）
_EXPANDED_DEFAULT = {"run_em", "run", "output", "output_md"}

# 参数说明（悬停提示，帮助用户理解物理含义）
_KEY_DESC = {
    "integrator":     "积分算法：steep/cg 用于能量最小化，md 用于动力学",
    "nsteps":         "总模拟步数。生产模拟常用 500000 步以上 (1 ns @ dt=2fs)",
    "dt":             "时间步长 (ps)。推荐 0.002 (2 fs)，与键长约束搭配",
    "emtol":          "能量最小化收敛判据 (kJ/mol/nm)。越小越严格",
    "emstep":         "最小化初始步长 (nm)。过大可能导致震荡",
    "nstxout":        "完整坐标轨迹输出频率（步）。0 表示不输出",
    "nstxout-compressed": "压缩轨迹输出频率（步）。分析主要用这个",
    "cutoff-scheme":  "截断方案。Verlet 为推荐方案（GPU 加速友好）",
    "coulombtype":    "静电相互作用算法。PME 为推荐方案",
    "rcoulomb":       "静电截断半径 (nm)。与 rvdw 保持一致",
    "rvdw":           "范德华截断半径 (nm)",
    "tcoupl":         "控温算法。V-rescale 适合平衡，nose-hoover 适合严格 NVT 系综",
    "ref_t":          "参考温度 (K)。一般设为实验温度如 300",
    "pcoupl":         "控压算法。Parrinello-Rahman 用于生产，berendsen 用于平衡",
    "ref_p":          "参考压力 (bar)。通常 1.0",
    "constraints":    "键长约束：h-bonds 约束含氢键，all-bonds 约束全部键",
    "continuation":   "续跑模式：yes 表示从先前模拟续跑（不重新生成初速度）",
    "gen_vel":        "是否生成初始速度。首次运行选 yes，续跑选 no",
    "gen_temp":       "初始速度对应的温度 (K)",
    "pbc":            "周期性边界条件。xyz 为三维周期（常用）",
}


class _CollapsibleSection(QWidget):
    """可折叠参数分区：点击标题栏展开/收起"""

    def __init__(self, title: str, expanded: bool = False, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        self._btn = QToolButton()
        self._btn.setText(title)
        self._btn.setCheckable(True)
        self._btn.setChecked(expanded)
        self._btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._btn.setAutoRaise(True)
        set_role(self._btn, "section")
        self._btn.clicked.connect(self._toggle)
        lay.addWidget(self._btn)

        self._content = QWidget()
        self._content.setVisible(expanded)
        lay.addWidget(self._content)

    def _toggle(self):
        self._content.setVisible(self._btn.isChecked())

    def layout(self) -> QFormLayout:
        """返回内容区的表单布局（惰性创建）"""
        if self._content.layout() is None:
            fl = QFormLayout(self._content)
            fl.setContentsMargins(8, 0, 0, 2)
            fl.setVerticalSpacing(3)
            fl.setHorizontalSpacing(12)
            fl.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
            self._content.setLayout(fl)
        return self._content.layout()


class MDPPanel(QWidget):
    """结构化 MDP 参数面板，直接嵌入标签页，取代 QTextEdit + MDPEditor 弹窗"""

    changed = pyqtSignal()

    def __init__(self, mdp_type="nvt", parent=None):
        super().__init__(parent)
        self.mdp_type = mdp_type
        self._widgets = {}       # key → QWidget
        self._extra_params = {}  # MDP 中 GUI 不覆盖的额外参数（保留不丢失）
        self._raw_visible = False
        self._raw_builtin = False  # raw QTextEdit 是否已构建
        self.init_ui()
        self._init_defaults()

    # ── UI ───────────────────────────────────────────────────────────────────
    def init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        form_w = QWidget(); self.form = QVBoxLayout(form_w)
        self.form.setContentsMargins(0, 0, 0, 0)
        self.form.setSpacing(0)

        sections = _MDP_TYPE_SECTIONS.get(self.mdp_type, [])
        for sec in sections:
            self._add_section(sec)
        self.form.addStretch()

        # raw preview toggle
        self.btn_toggle_raw = QPushButton(tr("▸ 显示原始 MDP 预览"))
        self.btn_toggle_raw.clicked.connect(self._toggle_raw)
        self.form.addWidget(self.btn_toggle_raw)

        self.raw_edit = QTextEdit()
        self.raw_edit.setObjectName("rawMdp")
        self.raw_edit.hide()
        self.form.addWidget(self.raw_edit)
        self._raw_builtin = True

        scroll.setWidget(form_w); root.addWidget(scroll)

    def _add_section(self, sec_name):
        keys = _SECTION_KEYS.get(sec_name, [])
        if not keys: return

        title = _SECTION_TITLES.get(sec_name, sec_name)
        sec = _CollapsibleSection(title, expanded=sec_name in _EXPANDED_DEFAULT)
        fl = sec.layout()
        for key in keys:
            wt = _WIDGET_TYPE.get(key, ("line", []))
            if wt[0] == "combo":
                w = QComboBox(); w.addItems(wt[1])
            else:
                w = QLineEdit()
            label = QLabel(f"{key}")
            desc = _KEY_DESC.get(key)
            if desc:
                label.setToolTip(desc)
                if isinstance(w, (QLineEdit, QComboBox)):
                    w.setToolTip(desc)
            fl.addRow(label, w)
            self._widgets[key] = w
        self.form.addWidget(sec)

    # ── defaults ─────────────────────────────────────────────────────────────
    def _init_defaults(self):
        """用默认值填充所有字段，不 emit changed"""
        for key, w in self._widgets.items():
            d = _DEFAULTS.get(key, "")
            if isinstance(w, QComboBox):
                idx = w.findText(d)
                if idx >= 0: w.setCurrentIndex(idx)
            elif isinstance(w, QLineEdit):
                w.setText(d)

    # ─── public API ──────────────────────────────────────────────────────────
    def set_mdp_text(self, text: str):
        """解析 MDP 文本并回填到表单中"""
        parsed, extra = self._parse(text)
        for key, w in self._widgets.items():
            if key in parsed:
                val = parsed[key]
                if isinstance(w, QComboBox):
                    idx = w.findText(val)
                    if idx >= 0: w.setCurrentIndex(idx)
                    else: w.setCurrentText(val)
                elif isinstance(w, QLineEdit):
                    w.setText(val)
            else:
                # 表单有的 key 但 MDP 里没有 → 用默认值
                d = _DEFAULTS.get(key, "")
                if isinstance(w, QLineEdit): w.setText(d)
        self._extra_params = extra
        self._refresh_raw()

    def get_mdp_text(self) -> str:
        """根据当前表单值和保留的额外参数生成 MDP 内容"""
        lines = [f"; Generated by GROMACS-GUI — {self.mdp_type.upper()}"]
        # 表单参数
        for key, w in self._widgets.items():
            if isinstance(w, QComboBox): val = w.currentText()
            elif isinstance(w, QLineEdit): val = w.text()
            else: continue
            lines.append(f"{key:<25} = {val}")
        # 保留的额外参数
        if self._extra_params:
            lines.append("\n; 以下为 MDP 中保留的其他参数")
            for k, v in self._extra_params.items():
                lines.append(f"{k:<25} = {v}")
        return "\n".join(lines) + "\n"

    # ─── parse ───────────────────────────────────────────────────────────────
    def _parse(self, text: str):
        parsed = {}
        extra = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith((";", "#")): continue
            if ";" in line:
                line = line.split(";")[0].strip()
            m = re.match(r"^([\w\-]+)\s*=\s*(.+)$", line)
            if not m: continue
            key, val = m.group(1).strip(), m.group(2).strip()
            if key in self._widgets:
                parsed[key] = val
            else:
                extra[key] = val
        return parsed, extra

    # ─── raw toggle ──────────────────────────────────────────────────────────
    def _toggle_raw(self):
        self._raw_visible = not self._raw_visible
        if self._raw_visible:
            self._refresh_raw()
            self.raw_edit.show()
            self.btn_toggle_raw.setText(tr("▾ 隐藏原始 MDP 预览"))
        else:
            self.raw_edit.hide()
            self.btn_toggle_raw.setText(tr("▸ 显示原始 MDP 预览"))

    def _refresh_raw(self):
        if self._raw_builtin:
            self.raw_edit.setPlainText(self.get_mdp_text())

    # ─── helpers ─────────────────────────────────────────────────────────────
    def get(self, key: str) -> str:
        """获取单个参数值"""
        w = self._widgets.get(key)
        if w is None: return ""
        if isinstance(w, QComboBox): return w.currentText()
        if isinstance(w, QLineEdit): return w.text()
        return ""

    def set(self, key: str, value: str):
        """设置单个参数值"""
        w = self._widgets.get(key)
        if w is None: return
        if isinstance(w, QComboBox):
            idx = w.findText(value)
            if idx >= 0: w.setCurrentIndex(idx)
        elif isinstance(w, QLineEdit):
            w.setText(value)
