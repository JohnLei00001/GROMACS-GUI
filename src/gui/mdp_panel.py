from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel, QGroupBox, QFormLayout,
                             QComboBox, QLineEdit, QTextEdit)
from PyQt6.QtCore import pyqtSignal
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
        form_w = QWidget(); self.form = QVBoxLayout(form_w)

        sections = _MDP_TYPE_SECTIONS.get(self.mdp_type, [])
        for sec in sections:
            self._add_section(sec)
        self.form.addStretch()

        # raw preview toggle
        self.btn_toggle_raw = QPushButton("▸ 显示原始 MDP 预览")
        self.btn_toggle_raw.clicked.connect(self._toggle_raw)
        self.form.addWidget(self.btn_toggle_raw)

        self.raw_edit = QTextEdit()
        self.raw_edit.setStyleSheet("font-family: Consolas; font-size: 9pt;")
        self.raw_edit.hide()
        self.form.addWidget(self.raw_edit)
        self._raw_builtin = True

        scroll.setWidget(form_w); root.addWidget(scroll)

    def _add_section(self, sec_name):
        keys = _SECTION_KEYS.get(sec_name, [])
        if not keys: return

        titles = {
            "run_em": "运行控制 (Run Control)",
            "run": "运行控制 (Run Control)",
            "output": "输出控制 (Output Control)",
            "output_md": "输出控制 (Output Control)",
            "neighbor": "邻居搜索与相互作用 (Neighbor Searching)",
            "electrostatics": "静电学 (Electrostatics)",
            "thermostat": "温度耦合 (Temperature Coupling)",
            "barostat": "压力耦合 (Pressure Coupling)",
            "constraints": "键长约束 (Constraints)",
            "continuation": "续跑设置 (Continuation)",
            "velocity": "初始速度生成 (Velocity Generation)",
            "pbc": "周期性边界条件 (PBC)",
        }
        g = QGroupBox(titles.get(sec_name, sec_name))
        fl = QFormLayout()
        for key in keys:
            wt = _WIDGET_TYPE.get(key, ("line", []))
            if wt[0] == "combo":
                w = QComboBox(); w.addItems(wt[1])
            else:
                w = QLineEdit()
            fl.addRow(f"{key}", w)
            self._widgets[key] = w
        g.setLayout(fl)
        self.form.addWidget(g)

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
            self.btn_toggle_raw.setText("▾ 隐藏原始 MDP 预览")
        else:
            self.raw_edit.hide()
            self.btn_toggle_raw.setText("▸ 显示原始 MDP 预览")

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
