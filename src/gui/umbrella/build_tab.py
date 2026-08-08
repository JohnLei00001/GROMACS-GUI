"""Umbrella Build Tab —— 体系构建（PDB 构建 / 导入已有体系）

设计原则：
- 构建完成后创建 UmbrellaContext，携带明确的 structure_file 和 topology_file
"""

from PyQt6.QtWidgets import (QFrame, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel, QStackedWidget,
                             QFormLayout, QComboBox, QLineEdit, QRadioButton,
                             QMessageBox, QFileDialog, QCheckBox)
from PyQt6.QtCore import pyqtSignal
from gui.topology_tab import discover_forcefields, strip_pdb_nonprotein
from gui.i18n import tr, trf
from gui.theme import set_role
from gui.widgets import StepCard
from .workflow_context import UmbrellaContext
import os, shutil


class BuildTab(QWidget):
    build_done = pyqtSignal(UmbrellaContext)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.runner = main_window.runner
        self.cwd = ""; self.pdb_filename = ""; self.mode = "build"
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget(); layout = QVBoxLayout(w); layout.setSpacing(10)

        mg_card = StepCard("", tr("体系来源"), layout_kind="vbox")
        ml = mg_card.content_layout; mh = QHBoxLayout()
        self.rb_build = QRadioButton(tr("从 PDB 构建")); self.rb_import = QRadioButton(tr("导入已有体系 (.gro + topol.top)"))
        self.rb_build.setChecked(True)
        self.rb_build.toggled.connect(self._on_mode); self.rb_import.toggled.connect(self._on_mode)
        mh.addWidget(self.rb_build); mh.addWidget(self.rb_import); mh.addStretch()
        ml.addLayout(mh)
        ml.addWidget(QLabel(tr("从 PDB 构建：pdb2gmx → solvate → genion\n导入已有体系：直接使用已制备好的 .gro + topol.top")))
        layout.addWidget(mg_card)

        dg_card = StepCard("", tr("工作目录"), layout_kind="vbox")
        dl = dg_card.content_layout
        self.dir_input = QLineEdit(); self.dir_input.setPlaceholderText(tr("选择文件后自动..."))
        btn = QPushButton(tr("浏览...")); btn.clicked.connect(self._browse_dir)
        dl.addWidget(self.dir_input); dl.addWidget(btn)
        layout.addWidget(dg_card)

        self.stack = QStackedWidget()
        bp = QWidget(); bl = QVBoxLayout(bp); bl.setContentsMargins(0,0,0,0)
        g1_card = StepCard(1, tr("pdb2gmx"))
        f1 = g1_card.content_layout
        fl = QHBoxLayout(); self.pdb_input = QLineEdit(); self.pdb_input.setPlaceholderText(tr("选择 .pdb..."))
        fl.addWidget(self.pdb_input); fl.addWidget(QPushButton(tr("浏览..."), clicked=self._browse_pdb))
        f1.addRow("PDB:", fl)
        self.ff = QComboBox(); self.ff.addItems(discover_forcefields()); self.ff.setCurrentText("amber99sb"); f1.addRow(tr("力场:"), self.ff)
        self.water = QComboBox(); self.water.addItems(["spce","tip3p","tip4p","tip5p"]); self.water.setCurrentText("spce"); f1.addRow(tr("水模型:"), self.water)
        self.ignh = QCheckBox(tr("忽略输入 H")); self.ignh.setChecked(True); f1.addRow("", self.ignh)
        self.btn_pdb2gmx = QPushButton(tr("▶ 运行 pdb2gmx")); self.btn_pdb2gmx.clicked.connect(self._run_pdb2gmx); set_role(self.btn_pdb2gmx, "primary"); f1.addRow("", self.btn_pdb2gmx)
        bl.addWidget(g1_card)
        g2_card = StepCard(2, tr("盒子 & 溶剂化"))
        f2 = g2_card.content_layout
        self.box_type = QComboBox(); self.box_type.addItems(["cubic","dodecahedron","octahedron"]); self.box_type.setCurrentText("cubic"); f2.addRow(tr("形状:"), self.box_type)
        self.box_dist = QLineEdit("1.0"); f2.addRow(tr("距离 (nm):"), self.box_dist)
        self.btn_solvate = QPushButton(tr("▶ 运行 editconf & solvate")); self.btn_solvate.clicked.connect(self._run_solvate); set_role(self.btn_solvate, "primary"); f2.addRow("", self.btn_solvate)
        bl.addWidget(g2_card)
        g3_card = StepCard(3, tr("添加离子"))
        f3 = g3_card.content_layout
        self.conc = QLineEdit("0.15"); f3.addRow(tr("盐浓度:"), self.conc)
        self.pname = QLineEdit("NA"); f3.addRow(tr("阳离子:"), self.pname)
        self.nname = QLineEdit("CL"); f3.addRow(tr("阴离子:"), self.nname)
        self.neutral = QCheckBox(tr("中和净电荷")); self.neutral.setChecked(True); f3.addRow("", self.neutral)
        self.btn_genion = QPushButton(tr("▶ 运行 grompp & genion")); self.btn_genion.clicked.connect(self._run_genion); set_role(self.btn_genion, "primary"); f3.addRow("", self.btn_genion)
        bl.addWidget(g3_card)
        self.stack.addWidget(bp)

        ip = QWidget(); il = QVBoxLayout(ip); il.setContentsMargins(0,0,0,0)
        gi_card = StepCard("", tr("导入已有体系"))
        fi = gi_card.content_layout
        hg = QHBoxLayout(); self.import_gro = QLineEdit(); self.import_gro.setPlaceholderText(tr("选择 .gro...")); hg.addWidget(self.import_gro); hg.addWidget(QPushButton(tr("浏览..."), clicked=self._browse_ig)); fi.addRow(tr("结构 (.gro):"), hg)
        ht = QHBoxLayout(); self.import_top = QLineEdit(); self.import_top.setPlaceholderText(tr("选择 topol.top...")); ht.addWidget(self.import_top); ht.addWidget(QPushButton(tr("浏览..."), clicked=self._browse_it)); fi.addRow(tr("拓扑:"), ht)
        fi.addRow(QLabel(tr("假设体系已完成溶剂化与离子添加。")))
        self.btn_import = QPushButton(tr("▶ 确认导入")); self.btn_import.clicked.connect(self._confirm_import); set_role(self.btn_import, "primary"); fi.addRow("", self.btn_import)
        il.addWidget(gi_card); il.addStretch()
        self.stack.addWidget(ip)
        layout.addWidget(self.stack)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    def _on_mode(self):
        self.mode = "build" if self.rb_build.isChecked() else "import"
        self.stack.setCurrentIndex(0 if self.mode == "build" else 1)

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, tr("工作目录"), self.cwd or os.getcwd())
        if d: self.cwd = d; self.dir_input.setText(d)

    def _browse_pdb(self):
        f, _ = QFileDialog.getOpenFileName(self, "PDB", self.cwd or os.getcwd(), "PDB (*.pdb)")
        if f:
            self.cwd = os.path.dirname(f); self.pdb_filename = os.path.basename(f)
            self.dir_input.setText(self.cwd)
            t = os.path.join(self.cwd, self.pdb_filename)
            if os.path.abspath(f) != os.path.abspath(t): shutil.copy(f, t)
            self.pdb_input.setText(self.pdb_filename)
            self.main_window.log(trf("已选择 PDB: {file} → {dir}", file=self.pdb_filename, dir=self.cwd))

    def _browse_ig(self):
        f, _ = QFileDialog.getOpenFileName(self, ".gro", self.cwd or os.getcwd(), "GRO (*.gro)")
        if f: self.cwd = os.path.dirname(f); self.dir_input.setText(self.cwd); self.import_gro.setText(os.path.basename(f))

    def _browse_it(self):
        f, _ = QFileDialog.getOpenFileName(self, "topol.top", self.cwd or os.getcwd(), "TOP (*.top);;All (*)")
        if f: self.cwd = os.path.dirname(f); self.dir_input.setText(self.cwd); self.import_top.setText(os.path.basename(f))

    def _confirm_import(self):
        gf = self.import_gro.text(); tf = self.import_top.text()
        if not gf or not tf: QMessageBox.warning(self, tr("警告"), tr("请选择 .gro 和 topol.top")); return
        gp = os.path.join(self.cwd, gf); tp = os.path.join(self.cwd, tf)
        if not os.path.exists(gp) or not os.path.exists(tp): QMessageBox.warning(self, tr("警告"), tr("文件不存在")); return
        shutil.copy(gp, os.path.join(self.cwd, "solvated_ions.gro"))
        if os.path.abspath(tp) != os.path.abspath(os.path.join(self.cwd, "topol.top")): shutil.copy(tp, os.path.join(self.cwd, "topol.top"))
        self.main_window.log(trf(">>> ✓ 导入: {gro} + {top}", gro=gf, top=tf))

        ctx = UmbrellaContext(cwd=self.cwd, structure_file="solvated_ions.gro", topology_file="topol.top")
        self.build_done.emit(ctx)

    def _run_pdb2gmx(self):
        if not self.pdb_filename or not self.cwd: return
        p = os.path.join(self.cwd, self.pdb_filename)
        if not os.path.exists(p): return
        r = strip_pdb_nonprotein(p)
        if r: self.main_window.log(trf(">>> 清理: {n} 个非蛋白残基", n=r))
        args = ["pdb2gmx","-f",self.pdb_filename,"-o","processed.gro","-p","topol.top","-ff",self.ff.currentText(),"-water",self.water.currentText(),"-ter"]
        if self.ignh.isChecked(): args.append("-ignh")
        self._setbtn(False); self._go(args, "1\n0\n", lambda s,m: self._done(s,m,"pdb2gmx"))

    def _run_solvate(self):
        self._setbtn(False)
        self._go(["editconf","-f","processed.gro","-o","newbox.gro","-c","-d",self.box_dist.text(),"-bt",self.box_type.currentText()],
                 on_finish=lambda s,m: self._on_ec(s,m))

    def _on_ec(self, s, m):
        if not s: self._setbtn(True); QMessageBox.critical(self,tr("错误"),trf("editconf: {msg}", msg=m)); return
        self._go(["solvate","-cp","newbox.gro","-cs","spc216.gro","-o","solvated.gro","-p","topol.top"],
                 on_finish=lambda s2,m2: self._done(s2,m2,"solvate"))

    def _run_genion(self):
        with open(os.path.join(self.cwd,"ions.mdp"),"w") as f:
            f.write("integrator = steep\nemtol = 1000.0\nemstep = 0.01\nnsteps = 50000\nnstlist = 1\ncutoff-scheme = Verlet\nns_type = grid\ncoulombtype = PME\nrcoulomb = 1.0\nrvdw = 1.0\npbc = xyz\n")
        self._setbtn(False)
        self._go(["grompp","-f","ions.mdp","-c","solvated.gro","-p","topol.top","-o","ions.tpr","-maxwarn","2"],
                 on_finish=lambda s,m: self._on_gi(s,m))

    def _on_gi(self, s, m):
        if not s: self._setbtn(True); QMessageBox.critical(self,tr("错误"),trf("genion grompp: {msg}", msg=m)); return
        a = ["genion","-s","ions.tpr","-o","solvated_ions.gro","-p","topol.top","-pname",self.pname.text(),"-nname",self.nname.text()]
        if self.neutral.isChecked(): a.append("-neutral")
        if self.conc.text(): a.extend(["-conc",self.conc.text()])
        self._go(a,"SOL\n", lambda s2,m2: self._done(s2,m2,"genion"))

    def _done(self, success, message, name):
        self._setbtn(True)
        if success:
            self.main_window.log(trf(">>> ✓ {name}", name=name))
            if name == "genion":
                ctx = UmbrellaContext(cwd=self.cwd, structure_file="solvated_ions.gro", topology_file="topol.top")
                self.build_done.emit(ctx)
        else:
            QMessageBox.critical(self,tr("错误"),trf("{name}: {msg}", name=name, msg=message))

    def _setbtn(self, e):
        for b in self.findChildren(QPushButton): b.setEnabled(e)

    def _go(self, args, input_text=None, on_finish=None):
        w = self.runner.create_worker(args, cwd=self.cwd, input_text=input_text)
        w.output_signal.connect(self.main_window.log)
        if on_finish: w.finished_signal.connect(on_finish)
        w.start()
