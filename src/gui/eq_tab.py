from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, 
                             QFormLayout, QComboBox, QLineEdit, 
                             QTextEdit, QMessageBox, QTabWidget, QDialog,
                             QScrollArea, QFrame)
import os
from gui.mdp_panel import MDPPanel
from gui.i18n import tr, trf
from gui.widgets import StepCard
from gui.theme import set_role

class EQTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        self.eq_tabs = QTabWidget()
        main_layout.addWidget(self.eq_tabs)

        # NVT
        self.nvt_tab = QWidget()
        self._init_nvt()
        self.eq_tabs.addTab(self.nvt_tab, tr("NVT 平衡 (恒温)"))

        # NPT
        self.npt_tab = QWidget()
        self._init_npt()
        self.eq_tabs.addTab(self.npt_tab, tr("NPT 平衡 (恒压)"))

    def _init_nvt(self):
        # 滚动容器：内容超高时允许滚动，避免窗口拉矮后被裁切
        root = QVBoxLayout(self.nvt_tab)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget(); layout = QVBoxLayout(w)
        layout.setSpacing(10)

        # 1. MDP
        mdp_card = StepCard(1, tr("准备 NVT 参数 (nvt.mdp)"), layout_kind="vbox")
        mdp_l = mdp_card.content_layout
        self.nvt_panel = MDPPanel("nvt")
        btn_row = QHBoxLayout()
        btn_save = QPushButton(tr("保存为 nvt.mdp"))
        btn_save.clicked.connect(lambda: self._save("nvt.mdp", self.nvt_panel.get_mdp_text()))
        set_role(btn_save, "primary")
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        mdp_l.addWidget(self.nvt_panel)
        mdp_l.addLayout(btn_row)
        layout.addWidget(mdp_card)

        # 2. 运行
        run_card = StepCard(2, tr("运行 NVT 平衡"), layout_kind="form")
        run_l = run_card.content_layout
        btn_grompp = QPushButton(tr("1. grompp (生成 nvt.tpr)"))
        btn_grompp.clicked.connect(self._run_grompp_nvt)
        set_role(btn_grompp, "primary")
        self.nvt_gpu = QComboBox()
        self.nvt_gpu.addItems(["自动检测", "强制使用 GPU", "仅使用 CPU"])
        btn_mdrun = QPushButton(tr("2. mdrun (执行 NVT)"))
        btn_mdrun.clicked.connect(self._run_mdrun_nvt)
        set_role(btn_mdrun, "primary")
        run_l.addRow(tr("预处理:"), btn_grompp)
        run_l.addRow(tr("硬件加速:"), self.nvt_gpu)
        run_l.addRow(tr("执行计算:"), btn_mdrun)
        layout.addWidget(run_card)
        scroll.setWidget(w); root.addWidget(scroll)

    def _init_npt(self):
        # 滚动容器：内容超高时允许滚动，避免窗口拉矮后被裁切
        root = QVBoxLayout(self.npt_tab)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget(); layout = QVBoxLayout(w)
        layout.setSpacing(10)

        mdp_card = StepCard(1, tr("准备 NPT 参数 (npt.mdp)"), layout_kind="vbox")
        mdp_l = mdp_card.content_layout
        self.npt_panel = MDPPanel("npt")
        btn_row = QHBoxLayout()
        btn_save = QPushButton(tr("保存为 npt.mdp"))
        btn_save.clicked.connect(lambda: self._save("npt.mdp", self.npt_panel.get_mdp_text()))
        set_role(btn_save, "primary")
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        mdp_l.addWidget(self.npt_panel)
        mdp_l.addLayout(btn_row)
        layout.addWidget(mdp_card)

        run_card = StepCard(2, tr("运行 NPT 平衡"), layout_kind="form")
        run_l = run_card.content_layout
        btn_grompp = QPushButton(tr("1. grompp (生成 npt.tpr)"))
        btn_grompp.clicked.connect(self._run_grompp_npt)
        set_role(btn_grompp, "primary")
        self.npt_gpu = QComboBox()
        self.npt_gpu.addItems(["自动检测", "强制使用 GPU", "仅使用 CPU"])
        btn_mdrun = QPushButton(tr("2. mdrun (执行 NPT)"))
        btn_mdrun.clicked.connect(self._run_mdrun_npt)
        set_role(btn_mdrun, "primary")
        run_l.addRow(tr("预处理:"), btn_grompp)
        run_l.addRow(tr("硬件加速:"), self.npt_gpu)
        run_l.addRow(tr("执行计算:"), btn_mdrun)
        layout.addWidget(run_card)
        scroll.setWidget(w); root.addWidget(scroll)

    # ─── helpers ────────────────────────────────────────────────────────
    def _cwd(self):
        try:
            idx = self.main_window.stacked_widget.currentIndex()
            if idx == 0: return self.main_window.solution_tabs.widget(0).cwd
            elif idx == 1: return self.main_window.ligand_simulator.prep_tab.cwd
        except: pass
        return None

    def _save(self, fn, content):
        cwd = self._cwd()
        if not cwd: QMessageBox.warning(self, tr("警告"), tr("请先在'拓扑与水箱'步骤中确定工作目录！")); return
        p = os.path.join(cwd, fn)
        with open(p, "w") as f: f.write(content)
        self.main_window.log(trf("已保存 {file} → {dir}", file=fn, dir=cwd))
        QMessageBox.information(self, tr("成功"), trf("{file} 已保存。", file=fn))

    def _set_btns(self, e):
        for b in self.findChildren(QPushButton): b.setEnabled(e)

    # ─── NVT ───────────────────────────────────────────────────────────
    def _run_grompp_nvt(self):
        cwd = self._cwd()
        if not cwd: return
        for f in ["nvt.mdp", "em.gro", "topol.top"]:
            if not os.path.exists(os.path.join(cwd, f)):
                QMessageBox.warning(self, tr("警告"), trf("缺少必要文件: {file}", file=f)); return
        self._set_btns(False)
        args = ["grompp", "-f", "nvt.mdp", "-c", "em.gro", "-r", "em.gro", "-p", "topol.top", "-o", "nvt.tpr", "-maxwarn", "1"]
        self.main_window.log(trf("\n>>> 正在运行: gmx {cmd}", cmd=" ".join(args)))
        w = self.runner.create_worker(args, cwd=cwd)
        w.output_signal.connect(self.main_window.log)
        w.finished_signal.connect(self._on_nvt_grompp)
        w.start()

    def _on_nvt_grompp(self, s, m):
        self._set_btns(True)
        QMessageBox.information(self, tr("成功"), tr("grompp 完成！生成了 nvt.tpr")) if s else QMessageBox.critical(self, tr("错误"), trf("grompp (NVT) 失败: {msg}", msg=m))

    def _run_mdrun_nvt(self):
        cwd = self._cwd()
        if not cwd or not os.path.exists(os.path.join(cwd, "nvt.tpr")): return
        self._set_btns(False)
        args = ["mdrun", "-v", "-deffnm", "nvt"]
        if self.nvt_gpu.currentIndex() == 1: args.extend(["-nb", "gpu"])
        elif self.nvt_gpu.currentIndex() == 2: args.extend(["-nb", "cpu"])
        self.main_window.log(trf("\n>>> 正在运行: gmx {cmd}", cmd=" ".join(args)))
        w = self.runner.create_worker(args, cwd=cwd)
        w.output_signal.connect(self.main_window.log)
        w.finished_signal.connect(self._on_nvt_mdrun)
        w.start()

    def _on_nvt_mdrun(self, s, m):
        self._set_btns(True)
        QMessageBox.information(self, tr("成功"), tr("NVT 平衡完成！")) if s else QMessageBox.critical(self, tr("错误"), trf("mdrun (NVT) 失败: {msg}", msg=m))

    # ─── NPT ───────────────────────────────────────────────────────────
    def _run_grompp_npt(self):
        cwd = self._cwd()
        if not cwd: return
        for f in ["npt.mdp", "nvt.gro", "topol.top"]:
            if not os.path.exists(os.path.join(cwd, f)):
                QMessageBox.warning(self, tr("警告"), trf("缺少必要文件: {file}", file=f)); return
        self._set_btns(False)
        args = ["grompp", "-f", "npt.mdp", "-c", "nvt.gro", "-r", "nvt.gro", "-p", "topol.top", "-o", "npt.tpr", "-maxwarn", "1"]
        if os.path.exists(os.path.join(cwd, "nvt.cpt")): args.insert(4, "nvt.cpt"); args.insert(4, "-t")
        self.main_window.log(trf("\n>>> 正在运行: gmx {cmd}", cmd=" ".join(args)))
        w = self.runner.create_worker(args, cwd=cwd)
        w.output_signal.connect(self.main_window.log)
        w.finished_signal.connect(self._on_npt_grompp)
        w.start()

    def _on_npt_grompp(self, s, m):
        self._set_btns(True)
        QMessageBox.information(self, tr("成功"), tr("grompp 完成！生成了 npt.tpr")) if s else QMessageBox.critical(self, tr("错误"), trf("grompp (NPT) 失败: {msg}", msg=m))

    def _run_mdrun_npt(self):
        cwd = self._cwd()
        if not cwd or not os.path.exists(os.path.join(cwd, "npt.tpr")): return
        self._set_btns(False)
        args = ["mdrun", "-v", "-deffnm", "npt"]
        if self.npt_gpu.currentIndex() == 1: args.extend(["-nb", "gpu"])
        elif self.npt_gpu.currentIndex() == 2: args.extend(["-nb", "cpu"])
        self.main_window.log(trf("\n>>> 正在运行: gmx {cmd}", cmd=" ".join(args)))
        w = self.runner.create_worker(args, cwd=cwd)
        w.output_signal.connect(self.main_window.log)
        w.finished_signal.connect(self._on_npt_mdrun)
        w.start()

    def _on_npt_mdrun(self, s, m):
        self._set_btns(True)
        QMessageBox.information(self, tr("成功"), tr("NPT 平衡完成！")) if s else QMessageBox.critical(self, tr("错误"), trf("mdrun (NPT) 失败: {msg}", msg=m))
