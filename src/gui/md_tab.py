from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QComboBox, QLineEdit, 
                             QMessageBox)
import os
from gui.mdp_panel import MDPPanel

class MDTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. MDP
        mdp_group = QGroupBox("1. 准备生产模拟参数 (md.mdp)")
        mdp_l = QVBoxLayout()
        self.mdp_panel = MDPPanel("md")
        btn_row = QHBoxLayout()
        btn_save = QPushButton("保存为 md.mdp")
        btn_save.clicked.connect(lambda: self._save("md.mdp", self.mdp_panel.get_mdp_text()))
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        mdp_l.addWidget(self.mdp_panel)
        mdp_l.addLayout(btn_row)
        mdp_group.setLayout(mdp_l)
        layout.addWidget(mdp_group)

        # 2. 运行
        run_group = QGroupBox("2. 运行生产模拟 (Production MD)")
        run_l = QFormLayout()
        btn_grompp = QPushButton("1. grompp (生成 md_0_1.tpr)")
        btn_grompp.clicked.connect(self._run_grompp)
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems(["自动检测", "强制使用 GPU", "仅使用 CPU"])
        btn_mdrun = QPushButton("2. mdrun (执行生产模拟)")
        btn_mdrun.clicked.connect(self._run_mdrun)
        run_l.addRow("预处理:", btn_grompp)
        run_l.addRow("硬件加速:", self.gpu_combo)
        run_l.addRow("执行计算:", btn_mdrun)
        run_group.setLayout(run_l)
        layout.addWidget(run_group)

    def _cwd(self):
        try:
            idx = self.main_window.stacked_widget.currentIndex()
            if idx == 0: return self.main_window.solution_tabs.widget(0).cwd
            elif idx == 1: return self.main_window.ligand_simulator.prep_tab.cwd
        except: pass
        return None

    def _save(self, fn, content):
        cwd = self._cwd()
        if not cwd: QMessageBox.warning(self, "警告", "请先在'拓扑与水箱'步骤中确定工作目录！"); return
        p = os.path.join(cwd, fn)
        with open(p, "w") as f: f.write(content)
        self.main_window.log(f"已保存 {fn} → {cwd}")
        QMessageBox.information(self, "成功", f"{fn} 已保存。")

    def _set_btns(self, e):
        for b in self.findChildren(QPushButton): b.setEnabled(e)

    def _run_grompp(self):
        cwd = self._cwd()
        if not cwd: return
        for f in ["md.mdp", "npt.gro", "topol.top", "npt.cpt"]:
            if not os.path.exists(os.path.join(cwd, f)):
                QMessageBox.warning(self, "警告", f"缺少必要文件: {f}"); return
        self._set_btns(False)
        args = ["grompp", "-f", "md.mdp", "-c", "npt.gro", "-t", "npt.cpt", "-p", "topol.top", "-o", "md_0_1.tpr", "-maxwarn", "1"]
        self.main_window.log(f"\n>>> 正在运行: gmx {' '.join(args)}")
        w = self.runner.create_worker(args, cwd=cwd)
        w.output_signal.connect(self.main_window.log)
        w.finished_signal.connect(self._on_grompp)
        w.start()

    def _on_grompp(self, s, m):
        self._set_btns(True)
        QMessageBox.information(self, "成功", "grompp 完成！生成了 md_0_1.tpr") if s else QMessageBox.critical(self, "错误", f"grompp (MD) 失败: {m}")

    def _run_mdrun(self):
        cwd = self._cwd()
        if not cwd or not os.path.exists(os.path.join(cwd, "md_0_1.tpr")): return
        self._set_btns(False)
        args = ["mdrun", "-v", "-deffnm", "md_0_1"]
        g = self.gpu_combo.currentText()
        if g == "强制使用 GPU": args.extend(["-nb", "gpu"])
        elif g == "仅使用 CPU": args.extend(["-nb", "cpu"])
        self.main_window.log(f"\n>>> 正在运行: gmx {' '.join(args)}")
        w = self.runner.create_worker(args, cwd=cwd)
        w.output_signal.connect(self.main_window.log)
        w.finished_signal.connect(self._on_mdrun)
        w.start()

    def _on_mdrun(self, s, m):
        self._set_btns(True)
        QMessageBox.information(self, "成功", "生产模拟完成！") if s else QMessageBox.critical(self, "错误", f"mdrun (MD) 失败: {m}")
