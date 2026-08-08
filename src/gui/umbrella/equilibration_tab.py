"""Equilibration Tab —— EM → NVT → NPT 串联执行

设计原则：
- 三步合并为一个标签页，MDP 参数全部可见可编辑
- "运行全部"按钮自动串联执行 EM → NVT → NPT
- 同时保留各步独立运行能力用于调试
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel, QFormLayout,
                             QComboBox, QTextEdit, QMessageBox, QDialog,
                             QProgressBar)
from PyQt6.QtCore import pyqtSignal
from gui.mdp_editor import MDPEditor
from gui.i18n import tr, trf
from gui.theme import set_role
from gui.widgets import StepCard
from .workflow_context import UmbrellaContext
import os


_EM_MDP = """integrator  = steep
emtol       = 1000.0
emstep      = 0.01
nsteps      = 50000
nstlist     = 1
cutoff-scheme = Verlet
ns_type     = grid
coulombtype = PME
rcoulomb    = 1.0
rvdw        = 1.0
pbc         = xyz"""

_NVT_MDP = """integrator              = md
nsteps                  = 50000
dt                      = 0.002
nstxout                 = 500
nstvout                 = 500
nstenergy               = 500
nstlog                  = 500
continuation            = no
constraint_algorithm    = lincs
constraints             = h-bonds
lincs_iter              = 1
lincs_order             = 4
cutoff-scheme           = Verlet
ns_type                 = grid
nstlist                 = 10
rcoulomb                = 1.0
rvdw                    = 1.0
DispCorr                = EnerPres
coulombtype             = PME
pme_order               = 4
fourierspacing          = 0.16
tcoupl                  = V-rescale
tc-grps                 = System
tau_t                   = 0.1
ref_t                   = 300
pcoupl                  = no
pbc                     = xyz
gen_vel                 = yes
gen_temp                = 300
gen_seed                = -1"""

_NPT_MDP = """integrator              = md
nsteps                  = 50000
dt                      = 0.002
nstxout                 = 500
nstvout                 = 500
nstenergy               = 500
nstlog                  = 500
continuation            = yes
constraint_algorithm    = lincs
constraints             = h-bonds
lincs_iter              = 1
lincs_order             = 4
cutoff-scheme           = Verlet
ns_type                 = grid
nstlist                 = 10
rcoulomb                = 1.0
rvdw                    = 1.0
DispCorr                = EnerPres
coulombtype             = PME
pme_order               = 4
fourierspacing          = 0.16
tcoupl                  = V-rescale
tc-grps                 = System
tau_t                   = 0.1
ref_t                   = 300
pcoupl                  = Parrinello-Rahman
pcoupltype              = isotropic
tau_p                   = 2.0
ref_p                   = 1.0
compressibility         = 4.5e-5
refcoord_scaling        = com
pbc                     = xyz
gen_vel                 = no"""


class EquilibrationTab(QWidget):
    eq_done = pyqtSignal(UmbrellaContext)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.ctx: UmbrellaContext = None
        self._running = False
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        w = QWidget(); layout = QVBoxLayout(w); layout.setSpacing(10)

        # ── 状态+GPU ──
        top_row = QHBoxLayout()
        self.status_label = QLabel(tr("等待体系构建完成..."))
        set_role(self.status_label, "muted")
        top_row.addWidget(self.status_label, stretch=1)
        top_row.addWidget(QLabel(tr("GPU:")))
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems(["自动检测", "强制使用 GPU", "仅使用 CPU"])
        top_row.addWidget(self.gpu_combo)
        layout.addLayout(top_row)

        # ── 进度条 ──
        self.progress = QProgressBar()
        self.progress.setMaximum(3)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # ── 1. EM ──
        g1_card = StepCard(1, tr("能量最小化 (EM)"), layout_kind="vbox")
        g1l = g1_card.content_layout
        mdp1_row = QHBoxLayout()
        self.em_mdp = QTextEdit()
        self.em_mdp.setText(_EM_MDP)
        self.em_mdp.setStyleSheet("font-family: Consolas; font-size: 9pt;")
        self.em_mdp.setMinimumHeight(130); self.em_mdp.setMaximumHeight(180)
        mdp1_row.addWidget(self.em_mdp, stretch=1)
        btn1_col = QVBoxLayout()
        btn_edit_em = QPushButton(tr("结构化编辑"), clicked=lambda: self._open_editor("em", self.em_mdp))
        set_role(btn_edit_em, "primary")
        btn1_col.addWidget(btn_edit_em)
        btn_run_em = QPushButton(tr("单独运行 EM"), clicked=self._run_em_only)
        set_role(btn_run_em, "primary")
        btn1_col.addWidget(btn_run_em)
        btn1_col.addStretch()
        mdp1_row.addLayout(btn1_col)
        g1l.addLayout(mdp1_row)
        layout.addWidget(g1_card)

        # ── 2. NVT ──
        g2_card = StepCard(2, tr("NVT 平衡"), layout_kind="vbox")
        g2l = g2_card.content_layout
        mdp2_row = QHBoxLayout()
        self.nvt_mdp = QTextEdit()
        self.nvt_mdp.setText(_NVT_MDP)
        self.nvt_mdp.setStyleSheet("font-family: Consolas; font-size: 9pt;")
        self.nvt_mdp.setMinimumHeight(200); self.nvt_mdp.setMaximumHeight(260)
        mdp2_row.addWidget(self.nvt_mdp, stretch=1)
        btn2_col = QVBoxLayout()
        btn_edit_nvt = QPushButton(tr("结构化编辑"), clicked=lambda: self._open_editor("nvt", self.nvt_mdp))
        set_role(btn_edit_nvt, "primary")
        btn2_col.addWidget(btn_edit_nvt)
        btn_run_nvt = QPushButton(tr("单独运行 NVT"), clicked=self._run_nvt_only)
        set_role(btn_run_nvt, "primary")
        btn2_col.addWidget(btn_run_nvt)
        btn2_col.addStretch()
        mdp2_row.addLayout(btn2_col)
        g2l.addLayout(mdp2_row)
        layout.addWidget(g2_card)

        # ── 3. NPT ──
        g3_card = StepCard(3, tr("NPT 平衡"), layout_kind="vbox")
        g3l = g3_card.content_layout
        mdp3_row = QHBoxLayout()
        self.npt_mdp = QTextEdit()
        self.npt_mdp.setText(_NPT_MDP)
        self.npt_mdp.setStyleSheet("font-family: Consolas; font-size: 9pt;")
        self.npt_mdp.setMinimumHeight(220); self.npt_mdp.setMaximumHeight(280)
        mdp3_row.addWidget(self.npt_mdp, stretch=1)
        btn3_col = QVBoxLayout()
        btn_edit_npt = QPushButton(tr("结构化编辑"), clicked=lambda: self._open_editor("npt", self.npt_mdp))
        set_role(btn_edit_npt, "primary")
        btn3_col.addWidget(btn_edit_npt)
        btn_run_npt = QPushButton(tr("单独运行 NPT"), clicked=self._run_npt_only)
        set_role(btn_run_npt, "primary")
        btn3_col.addWidget(btn_run_npt)
        btn3_col.addStretch()
        mdp3_row.addLayout(btn3_col)
        g3l.addLayout(mdp3_row)
        layout.addWidget(g3_card)

        # ── 主操作按钮 ──
        action_row = QHBoxLayout()
        self.btn_all = QPushButton(tr("▶ 运行全部平衡阶段 (EM → NVT → NPT)"))
        set_role(self.btn_all, "primary")
        self.btn_all.clicked.connect(self._run_all)
        action_row.addWidget(self.btn_all)
        action_row.addStretch()
        layout.addLayout(action_row)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    # ── 公共接口 ──

    def update_context(self, ctx: UmbrellaContext):
        self.ctx = ctx
        self.status_label.setText(trf("工作目录: {dir}  |  输入: {file}", dir=ctx.cwd, file=ctx.structure_file))
        set_role(self.status_label, "ok")

    # ── MDP 编辑 ──

    def _open_editor(self, mdp_type, text_edit):
        dlg = MDPEditor(self, mdp_type, text_edit.toPlainText())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            text_edit.setText(dlg.get_mdp_content())

    def _gpu_args(self):
        if self.gpu_combo.currentIndex() == 1: return ["-nb", "gpu"]
        elif self.gpu_combo.currentIndex() == 2: return ["-nb", "cpu"]
        return []

    # ── 运行全部 ──

    def _run_all(self):
        if not self.ctx:
            QMessageBox.warning(self, tr("提示"), tr("请先完成体系构建。")); return
        s = self.ctx.resolve(self.ctx.structure_file)
        t = self.ctx.resolve(self.ctx.topology_file)
        if not os.path.exists(s) or not os.path.exists(t):
            QMessageBox.warning(self, tr("提示"), tr("未找到输入结构或拓扑文件。")); return

        self._running = True
        self.btn_all.setEnabled(False)
        self.progress.setVisible(True); self.progress.setValue(0)
        self.status_label.setText(tr("EM 运行中..."))
        set_role(self.status_label, "running")

        # Step 1: 保存 EM MDP
        try:
            with open(self.ctx.resolve("minim.mdp"), "w") as f:
                f.write(self.em_mdp.toPlainText())
        except Exception as e:
            self._on_error(trf("保存 minim.mdp 失败: {err}", err=e)); return

        args = ["grompp", "-f", "minim.mdp", "-c", self.ctx.structure_file,
                "-p", self.ctx.topology_file, "-o", "em.tpr", "-maxwarn", "1"]
        self._start_worker(args, on_finish=lambda s, m: self._on_em_grompp(s, m))

    def _on_em_grompp(self, success, message):
        if not success: self._on_error(trf("EM grompp: {msg}", msg=message)); return
        self.main_window.log(tr(">>> [平衡] EM grompp 完成"))
        args = ["mdrun", "-v", "-deffnm", "em"] + self._gpu_args()
        self._start_worker(args, on_finish=lambda s, m: self._on_em_mdrun(s, m))

    def _on_em_mdrun(self, success, message):
        if not success: self._on_error(trf("EM mdrun: {msg}", msg=message)); return
        self.main_window.log(tr(">>> [平衡] EM 完成"))
        self.progress.setValue(1)
        self.status_label.setText(tr("NVT 运行中..."))
        self._run_nvt()

    def _run_nvt(self):
        try:
            with open(self.ctx.resolve("nvt.mdp"), "w") as f:
                f.write(self.nvt_mdp.toPlainText())
        except Exception as e:
            self._on_error(trf("保存 nvt.mdp 失败: {err}", err=e)); return
        args = ["grompp", "-f", "nvt.mdp", "-c", "em.gro", "-r", "em.gro",
                "-p", self.ctx.topology_file, "-o", "nvt.tpr", "-maxwarn", "1"]
        self._start_worker(args, on_finish=lambda s, m: self._on_nvt_grompp(s, m))

    def _on_nvt_grompp(self, success, message):
        if not success: self._on_error(trf("NVT grompp: {msg}", msg=message)); return
        self.main_window.log(tr(">>> [平衡] NVT grompp 完成"))
        args = ["mdrun", "-v", "-deffnm", "nvt"] + self._gpu_args()
        self._start_worker(args, on_finish=lambda s, m: self._on_nvt_mdrun(s, m))

    def _on_nvt_mdrun(self, success, message):
        if not success: self._on_error(trf("NVT mdrun: {msg}", msg=message)); return
        self.main_window.log(tr(">>> [平衡] NVT 完成"))
        self.progress.setValue(2)
        self.status_label.setText(tr("NPT 运行中..."))
        self._run_npt()

    def _run_npt(self):
        try:
            with open(self.ctx.resolve("npt.mdp"), "w") as f:
                f.write(self.npt_mdp.toPlainText())
        except Exception as e:
            self._on_error(trf("保存 npt.mdp 失败: {err}", err=e)); return
        args = ["grompp", "-f", "npt.mdp", "-c", "nvt.gro", "-r", "nvt.gro",
                "-p", self.ctx.topology_file, "-o", "npt.tpr", "-maxwarn", "1"]
        cpt = self.ctx.resolve("nvt.cpt")
        if os.path.exists(cpt):
            args.insert(4, cpt); args.insert(4, "-t")
        self._start_worker(args, on_finish=lambda s, m: self._on_npt_grompp(s, m))

    def _on_npt_grompp(self, success, message):
        if not success: self._on_error(trf("NPT grompp: {msg}", msg=message)); return
        self.main_window.log(tr(">>> [平衡] NPT grompp 完成"))
        args = ["mdrun", "-v", "-deffnm", "npt"] + self._gpu_args()
        self._start_worker(args, on_finish=lambda s, m: self._on_npt_mdrun(s, m))

    def _on_npt_mdrun(self, success, message):
        if not success: self._on_error(trf("NPT mdrun: {msg}", msg=message)); return
        self.main_window.log(tr(">>> [平衡] NPT 完成"))
        self.progress.setValue(3)
        self._running = False
        self.btn_all.setEnabled(True)
        self.status_label.setText(tr("平衡阶段完成"))
        set_role(self.status_label, "ok")
        QMessageBox.information(self, tr("完成"), tr("平衡阶段 (EM → NVT → NPT) 完成！\n请继续到「Pull 模拟」。"))
        self.eq_done.emit(self.ctx)

    # ── 单独运行（调试用） ──

    def _run_em_only(self):
        if not self.ctx: return
        s = self.ctx.resolve(self.ctx.structure_file)
        t = self.ctx.resolve(self.ctx.topology_file)
        if not os.path.exists(s) or not os.path.exists(t):
            QMessageBox.warning(self, tr("提示"), tr("未找到输入文件。")); return
        with open(self.ctx.resolve("minim.mdp"), "w") as f:
            f.write(self.em_mdp.toPlainText())
        self._start_worker(["grompp", "-f", "minim.mdp", "-c", self.ctx.structure_file,
                            "-p", self.ctx.topology_file, "-o", "em.tpr", "-maxwarn", "1"],
                           on_finish=lambda s, m: (
                               self._start_worker(["mdrun", "-v", "-deffnm", "em"] + self._gpu_args(),
                                                  on_finish=lambda s2, m2:
                                                  QMessageBox.information(self, "EM", tr("完成") if s2 else trf("失败: {msg}", msg=m2)))
                               if s else QMessageBox.critical(self, "EM", trf("grompp 失败: {msg}", msg=m))))

    def _run_nvt_only(self):
        if not self.ctx: return
        g = self.ctx.resolve("em.gro")
        if not os.path.exists(g):
            QMessageBox.warning(self, tr("提示"), tr("未找到 em.gro，请先运行 EM。")); return
        with open(self.ctx.resolve("nvt.mdp"), "w") as f:
            f.write(self.nvt_mdp.toPlainText())
        self._start_worker(["grompp", "-f", "nvt.mdp", "-c", "em.gro", "-r", "em.gro",
                            "-p", self.ctx.topology_file, "-o", "nvt.tpr", "-maxwarn", "1"],
                           on_finish=lambda s, m: (
                               self._start_worker(["mdrun", "-v", "-deffnm", "nvt"] + self._gpu_args(),
                                                  on_finish=lambda s2, m2:
                                                  QMessageBox.information(self, "NVT", tr("完成") if s2 else trf("失败: {msg}", msg=m2)))
                               if s else QMessageBox.critical(self, "NVT", trf("grompp 失败: {msg}", msg=m))))

    def _run_npt_only(self):
        if not self.ctx: return
        g = self.ctx.resolve("nvt.gro")
        if not os.path.exists(g):
            QMessageBox.warning(self, tr("提示"), tr("未找到 nvt.gro，请先运行 NVT。")); return
        with open(self.ctx.resolve("npt.mdp"), "w") as f:
            f.write(self.npt_mdp.toPlainText())
        args = ["grompp", "-f", "npt.mdp", "-c", "nvt.gro", "-r", "nvt.gro",
                "-p", self.ctx.topology_file, "-o", "npt.tpr", "-maxwarn", "1"]
        cpt = self.ctx.resolve("nvt.cpt")
        if os.path.exists(cpt):
            args.insert(4, cpt); args.insert(4, "-t")
        self._start_worker(args,
                           on_finish=lambda s, m: (
                               self._start_worker(["mdrun", "-v", "-deffnm", "npt"] + self._gpu_args(),
                                                  on_finish=lambda s2, m2:
                                                  QMessageBox.information(self, "NPT", tr("完成") if s2 else trf("失败: {msg}", msg=m2)))
                               if s else QMessageBox.critical(self, "NPT", trf("grompp 失败: {msg}", msg=m))))

    # ── 错误处理 ──

    def _on_error(self, msg):
        self._running = False
        self.btn_all.setEnabled(True)
        self.progress.setVisible(False)
        self.status_label.setText(tr("平衡失败"))
        set_role(self.status_label, "error")
        self.main_window.log(trf(">>> [平衡] 错误: {msg}", msg=msg))
        QMessageBox.critical(self, tr("平衡阶段错误"), msg)

    # ── Worker ──

    def _start_worker(self, args, input_text=None, on_finish=None):
        w = self.runner.create_worker(args, cwd=self.ctx.cwd, input_text=input_text)
        w.output_signal.connect(self.main_window.log)
        if on_finish:
            w.finished_signal.connect(on_finish)
        w.start()
