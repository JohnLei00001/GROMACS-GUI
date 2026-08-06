from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel, QGroupBox, QFormLayout,
                             QComboBox, QMessageBox)
from PyQt6.QtCore import pyqtSignal
from gui.mdp_panel import MDPPanel
import os

class NvtTab(QWidget):
    nvt_done = pyqtSignal(str)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.cwd = ""
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        w = QWidget(); layout = QVBoxLayout(w)

        self.status = QLabel("等待 EM 完成...")
        self.status.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.status)

        mdp_group = QGroupBox("1. 准备 NVT 参数 (nvt.mdp)")
        mdp_l = QVBoxLayout()
        self.mdp_panel = MDPPanel("nvt")
        btn_row = QHBoxLayout()
        btn_save = QPushButton("保存为 nvt.mdp")
        btn_save.clicked.connect(self._save_mdp)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        mdp_l.addWidget(self.mdp_panel)
        mdp_l.addLayout(btn_row)
        mdp_group.setLayout(mdp_l)
        layout.addWidget(mdp_group)

        grompp_group = QGroupBox("2. 生成运行文件 (grompp)")
        grompp_l = QFormLayout()
        self.btn_grompp = QPushButton("运行 grompp")
        self.btn_grompp.clicked.connect(self._run_grompp)
        grompp_l.addRow("执行预处理:", self.btn_grompp)
        grompp_group.setLayout(grompp_l)
        layout.addWidget(grompp_group)

        mdrun_group = QGroupBox("3. 执行 NVT 平衡 (mdrun)")
        mdrun_l = QFormLayout()
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems(["自动检测", "强制使用 GPU", "仅使用 CPU"])
        mdrun_l.addRow("硬件加速:", self.gpu_combo)
        self.btn_mdrun = QPushButton("运行 mdrun")
        self.btn_mdrun.clicked.connect(self._run_mdrun)
        mdrun_l.addRow("执行计算:", self.btn_mdrun)
        mdrun_group.setLayout(mdrun_l)
        layout.addWidget(mdrun_group)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    def update_cwd(self, cwd):
        self.cwd = cwd
        self.status.setText(f"✅ 工作目录: {cwd}")
        self.status.setStyleSheet("color: green; font-weight: bold;")

    def _save_mdp(self):
        if not self.cwd: return
        with open(os.path.join(self.cwd, "nvt.mdp"), "w") as f:
            f.write(self.mdp_panel.get_mdp_text())
        self.main_window.log("已保存 nvt.mdp")

    def _run_grompp(self):
        if not self.cwd: return
        for f in ["nvt.mdp", "em.gro", "topol.top"]:
            if not os.path.exists(os.path.join(self.cwd, f)):
                QMessageBox.warning(self, "警告", f"缺少 {f}"); return
        self._set_btns(False)
        self._go(["grompp", "-f", "nvt.mdp", "-c", "em.gro", "-r", "em.gro",
                  "-p", "topol.top", "-o", "nvt.tpr", "-maxwarn", "1"],
                 on_finish=lambda s, m: self._on_grompp_done(s, m))

    def _on_grompp_done(self, s, m):
        self._set_btns(True)
        if not s: QMessageBox.critical(self, "错误", f"grompp (NVT): {m}")

    def _run_mdrun(self):
        if not self.cwd or not os.path.exists(os.path.join(self.cwd, "nvt.tpr")): return
        args = ["mdrun", "-v", "-deffnm", "nvt"]
        g = self.gpu_combo.currentText()
        if g == "强制使用 GPU": args.extend(["-nb", "gpu"])
        elif g == "仅使用 CPU": args.extend(["-nb", "cpu"])
        self._set_btns(False)
        self._go(args, on_finish=lambda s, m: self._on_mdrun_done(s, m))

    def _on_mdrun_done(self, s, m):
        self._set_btns(True)
        if s:
            self.main_window.log(">>> ✓ NVT 完成")
            self.nvt_done.emit(self.cwd)
        else:
            QMessageBox.critical(self, "错误", f"mdrun (NVT): {m}")

    def _set_btns(self, e):
        for b in self.findChildren(QPushButton): b.setEnabled(e)

    def _go(self, args, input_text=None, on_finish=None):
        w = self.runner.create_worker(args, cwd=self.cwd, input_text=input_text)
        w.output_signal.connect(self.main_window.log)
        if on_finish: w.finished_signal.connect(on_finish)
        w.start()
