from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, 
                             QFormLayout, QComboBox, QLineEdit, 
                             QMessageBox, QScrollArea, QFrame)
import os
from gui.mdp_panel import MDPPanel
from gui.i18n import tr, trf
from gui.widgets import StepCard
from gui.theme import set_role

class MDTab(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.runner = main_window.runner
        self.init_ui()

    def init_ui(self):
        # 滚动容器：内容超高时允许滚动，避免窗口拉矮后被裁切
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget(); layout = QVBoxLayout(w)
        layout.setSpacing(10)

        # 1. MDP
        mdp_card = StepCard(1, tr("准备生产模拟参数 (md.mdp)"), layout_kind="vbox")
        mdp_l = mdp_card.content_layout
        self.mdp_panel = MDPPanel("md")
        btn_row = QHBoxLayout()
        btn_save = QPushButton(tr("保存为 md.mdp"))
        btn_save.clicked.connect(lambda: self._save("md.mdp", self.mdp_panel.get_mdp_text()))
        set_role(btn_save, "primary")
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        mdp_l.addWidget(self.mdp_panel)
        mdp_l.addLayout(btn_row)
        layout.addWidget(mdp_card)

        # 2. 运行
        run_card = StepCard(2, tr("运行生产模拟 (Production MD)"), layout_kind="form")
        run_l = run_card.content_layout
        btn_grompp = QPushButton(tr("1. grompp (生成 md_0_1.tpr)"))
        btn_grompp.clicked.connect(self._run_grompp)
        set_role(btn_grompp, "primary")
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems([tr("自动检测"), tr("强制使用 GPU"), tr("仅使用 CPU")])
        btn_mdrun = QPushButton(tr("2. mdrun (执行生产模拟)"))
        btn_mdrun.clicked.connect(self._run_mdrun)
        set_role(btn_mdrun, "primary")
        run_l.addRow(tr("预处理:"), btn_grompp)
        run_l.addRow(tr("硬件加速:"), self.gpu_combo)
        run_l.addRow(tr("执行计算:"), btn_mdrun)
        layout.addWidget(run_card)

        scroll.setWidget(w); root.addWidget(scroll)

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

    def _run_grompp(self):
        cwd = self._cwd()
        if not cwd: return
        for f in ["md.mdp", "npt.gro", "topol.top", "npt.cpt"]:
            if not os.path.exists(os.path.join(cwd, f)):
                QMessageBox.warning(self, tr("警告"), trf("缺少必要文件: {file}", file=f)); return
        self._set_btns(False)
        args = ["grompp", "-f", "md.mdp", "-c", "npt.gro", "-t", "npt.cpt", "-p", "topol.top", "-o", "md_0_1.tpr", "-maxwarn", "1"]
        self.main_window.log(trf("\n>>> 正在运行: gmx {cmd}", cmd=" ".join(args)))
        w = self.runner.create_worker(args, cwd=cwd)
        w.output_signal.connect(self.main_window.log)
        w.finished_signal.connect(self._on_grompp)
        w.start()

    def _on_grompp(self, s, m):
        self._set_btns(True)
        QMessageBox.information(self, tr("成功"), tr("grompp 完成！生成了 md_0_1.tpr")) if s else QMessageBox.critical(self, tr("错误"), trf("grompp (MD) 失败: {msg}", msg=m))

    def _run_mdrun(self):
        cwd = self._cwd()
        if not cwd or not os.path.exists(os.path.join(cwd, "md_0_1.tpr")): return
        self._set_btns(False)
        args = ["mdrun", "-v", "-deffnm", "md_0_1"]
        if self.gpu_combo.currentIndex() == 1: args.extend(["-nb", "gpu"])
        elif self.gpu_combo.currentIndex() == 2: args.extend(["-nb", "cpu"])
        self.main_window.log(trf("\n>>> 正在运行: gmx {cmd}", cmd=" ".join(args)))
        w = self.runner.create_worker(args, cwd=cwd)
        w.output_signal.connect(self.main_window.log)
        w.finished_signal.connect(self._on_mdrun)
        w.start()

    def _on_mdrun(self, s, m):
        self._set_btns(True)
        QMessageBox.information(self, tr("成功"), tr("生产模拟完成！")) if s else QMessageBox.critical(self, tr("错误"), trf("mdrun (MD) 失败: {msg}", msg=m))
