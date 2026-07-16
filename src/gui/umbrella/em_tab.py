from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QScrollArea,
                             QPushButton, QLabel, QGroupBox,
                             QFormLayout, QLineEdit, QMessageBox)
from PyQt6.QtCore import pyqtSignal
import os

class EmTab(QWidget):
    em_done = pyqtSignal(str)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.cwd = ""
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        s = QScrollArea(); s.setWidgetResizable(True); w = QWidget(); l = QVBoxLayout(w)

        self.status = QLabel("等待体系构建..."); self.status.setStyleSheet("color:red; font-weight:bold;")
        l.addWidget(self.status)

        g = QGroupBox("能量最小化 (EM)"); f = QFormLayout()
        self.nsteps = QLineEdit("50000"); f.addRow("步数:", self.nsteps)
        self.emtol = QLineEdit("1000.0"); f.addRow("容差:", self.emtol)
        self.btn = QPushButton("▶ 运行 EM"); self.btn.clicked.connect(self.run); f.addRow("", self.btn)
        g.setLayout(f); l.addWidget(g)

        l.addStretch()
        s.setWidget(w); root.addWidget(s)

    def update_cwd(self, cwd):
        self.cwd = cwd
        self.status.setText(f"✅ 工作目录: {cwd}"); self.status.setStyleSheet("color:green; font-weight:bold;")

    def run(self):
        if not self.cwd: return
        mdp = os.path.join(self.cwd, "em.mdp")
        with open(mdp, "w") as f:
            f.write(f"integrator = steep\nemtol = {self.emtol.text()}\nemstep = 0.01\nnsteps = {self.nsteps.text()}\n"
                    "nstlist = 1\ncutoff-scheme = Verlet\nns_type = grid\ncoulombtype = PME\nrcoulomb = 1.0\nrvdw = 1.0\npbc = xyz\n")
        self.btn.setEnabled(False)
        self._go(["grompp","-f","em.mdp","-c","solvated_ions.gro","-p","topol.top","-o","em.tpr","-maxwarn","2"],
                 on_finish=lambda s,m: self._on_grompp(s,m))
    def _on_grompp(self, s, m):
        if not s: self.btn.setEnabled(True); QMessageBox.critical(self,"错误",f"EM grompp: {m}"); return
        self._go(["mdrun","-deffnm","em","-v"], on_finish=lambda s2,m2: self._done(s2,m2))
    def _done(self, s, m):
        self.btn.setEnabled(True)
        if s: self.main_window.log(">>> ✓ EM 完成"); self.em_done.emit(self.cwd)
        else: QMessageBox.critical(self,"错误",f"EM mdrun: {m}")
    def _go(self, args, input_text=None, on_finish=None):
        w = self.runner.create_worker(args, cwd=self.cwd, input_text=input_text)
        w.output_signal.connect(self.main_window.log)
        if on_finish: w.finished_signal.connect(on_finish)
        w.start()
