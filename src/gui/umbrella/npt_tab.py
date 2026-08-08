from PyQt6.QtWidgets import (QFrame, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel, QFormLayout,
                             QComboBox, QMessageBox)
from PyQt6.QtCore import pyqtSignal
from gui.mdp_panel import MDPPanel
from gui.i18n import tr, trf
from gui.theme import set_role
from gui.widgets import StepCard
import os

class NptTab(QWidget):
    npt_done = pyqtSignal(str)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.runner = main_window.runner
        self.cwd = ""
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget(); layout = QVBoxLayout(w); layout.setSpacing(10)

        self.status = QLabel(tr("等待 NVT 完成..."))
        set_role(self.status, "error")
        layout.addWidget(self.status)

        mdp_card = StepCard(1, tr("准备 NPT 参数 (npt.mdp)"), layout_kind="vbox")
        mdp_l = mdp_card.content_layout
        self.mdp_panel = MDPPanel("npt")
        btn_row = QHBoxLayout()
        btn_save = QPushButton(tr("保存为 npt.mdp"))
        btn_save.clicked.connect(self._save_mdp)
        set_role(btn_save, "primary")
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        mdp_l.addWidget(self.mdp_panel)
        mdp_l.addLayout(btn_row)
        layout.addWidget(mdp_card)

        grompp_card = StepCard(2, tr("生成运行文件 (grompp)"))
        grompp_l = grompp_card.content_layout
        self.btn_grompp = QPushButton(tr("运行 grompp"))
        self.btn_grompp.clicked.connect(self._run_grompp)
        set_role(self.btn_grompp, "primary")
        grompp_l.addRow(tr("执行预处理:"), self.btn_grompp)
        layout.addWidget(grompp_card)

        mdrun_card = StepCard(3, tr("执行 NPT 平衡 (mdrun)"))
        mdrun_l = mdrun_card.content_layout
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems([tr("自动检测"), tr("强制使用 GPU"), tr("仅使用 CPU")])
        mdrun_l.addRow(tr("硬件加速:"), self.gpu_combo)
        self.btn_mdrun = QPushButton(tr("运行 mdrun"))
        self.btn_mdrun.clicked.connect(self._run_mdrun)
        set_role(self.btn_mdrun, "primary")
        mdrun_l.addRow(tr("执行计算:"), self.btn_mdrun)
        layout.addWidget(mdrun_card)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    def update_cwd(self, cwd):
        self.cwd = cwd
        self.status.setText(trf("✅ 工作目录: {dir}", dir=cwd))
        set_role(self.status, "ok")

    def _save_mdp(self):
        if not self.cwd: return
        with open(os.path.join(self.cwd, "npt.mdp"), "w") as f:
            f.write(self.mdp_panel.get_mdp_text())
        self.main_window.log(tr("已保存 npt.mdp"))

    def _run_grompp(self):
        if not self.cwd: return
        for f in ["npt.mdp", "nvt.gro", "topol.top"]:
            if not os.path.exists(os.path.join(self.cwd, f)):
                QMessageBox.warning(self, tr("警告"), trf("缺少 {file}", file=f)); return
        self._set_btns(False)
        args = ["grompp", "-f", "npt.mdp", "-c", "nvt.gro", "-r", "nvt.gro",
                "-p", "topol.top", "-o", "npt.tpr", "-maxwarn", "1"]
        if os.path.exists(os.path.join(self.cwd, "nvt.cpt")):
            args.insert(4, "nvt.cpt"); args.insert(4, "-t")
        self._go(args, on_finish=lambda s, m: self._on_grompp_done(s, m))

    def _on_grompp_done(self, s, m):
        self._set_btns(True)
        if not s: QMessageBox.critical(self, tr("错误"), trf("grompp (NPT): {msg}", msg=m))

    def _run_mdrun(self):
        if not self.cwd or not os.path.exists(os.path.join(self.cwd, "npt.tpr")): return
        args = ["mdrun", "-v", "-deffnm", "npt"]
        if self.gpu_combo.currentIndex() == 1: args.extend(["-nb", "gpu"])
        elif self.gpu_combo.currentIndex() == 2: args.extend(["-nb", "cpu"])
        self._set_btns(False)
        self._go(args, on_finish=lambda s, m: self._on_mdrun_done(s, m))

    def _on_mdrun_done(self, s, m):
        self._set_btns(True)
        if s:
            self.main_window.log(tr(">>> ✓ NPT 完成"))
            self.npt_done.emit(self.cwd)
        else:
            QMessageBox.critical(self, tr("错误"), trf("mdrun (NPT): {msg}", msg=m))

    def _set_btns(self, e):
        for b in self.findChildren(QPushButton): b.setEnabled(e)

    def _go(self, args, input_text=None, on_finish=None):
        w = self.runner.create_worker(args, cwd=self.cwd, input_text=input_text)
        w.output_signal.connect(self.main_window.log)
        if on_finish: w.finished_signal.connect(on_finish)
        w.start()
