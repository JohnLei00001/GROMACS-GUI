from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QScrollArea,
                             QPushButton, QLabel, QGroupBox,
                             QFormLayout, QLineEdit, QComboBox, QMessageBox)
from PyQt6.QtCore import pyqtSignal
import os

class NptTab(QWidget):
    npt_done = pyqtSignal(str)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window; self.runner = main_window.runner; self.cwd = ""
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self); s = QScrollArea(); s.setWidgetResizable(True); w = QWidget(); l = QVBoxLayout(w)
        self.status = QLabel("等待 NVT..."); self.status.setStyleSheet("color:red; font-weight:bold;"); l.addWidget(self.status)
        g = QGroupBox("NPT 平衡"); f = QFormLayout()
        self.nsteps = QLineEdit("50000"); f.addRow("步数:", self.nsteps)
        self.temp = QLineEdit("300"); f.addRow("温度 (K):", self.temp)
        self.dt = QLineEdit("0.002"); f.addRow("步长 dt (ps):", self.dt)
        self.pcoupl = QComboBox()
        self.pcoupl.addItems(["isotropic", "semiisotropic", "anisotropic", "surface-tension"])
        self.pcoupl.setCurrentText("isotropic"); f.addRow("压力耦合:", self.pcoupl)
        self.refp = QLineEdit("1.0"); f.addRow("参考压力 (bar):", self.refp)
        self.btn = QPushButton("▶ 运行 NPT"); self.btn.clicked.connect(self.run); f.addRow("", self.btn)
        g.setLayout(f); l.addWidget(g); l.addStretch()
        s.setWidget(w); root.addWidget(s)

    def update_cwd(self, cwd):
        self.cwd = cwd; self.status.setText(f"✅ {cwd}"); self.status.setStyleSheet("color:green;")

    def run(self):
        if not self.cwd: return
        ns = self.nsteps.text(); t = self.temp.text(); dt = self.dt.text()
        pct = self.pcoupl.currentText(); rp = self.refp.text()
        with open(os.path.join(self.cwd,"npt.mdp"),"w") as f:
            f.write(f"integrator = md\ndt = {dt}\nnsteps = {ns}\n"
                    "nstxout = 5000\nnstvout = 5000\nnstenergy = 5000\nnstlog = 5000\n"
                    f"tcoupl = V-rescale\ntc-grps = System\ntau-t = 0.1\nref-t = {t}\n"
                    f"pcoupl = Parrinello-Rahman\npcoupltype = {pct}\ntau-p = 2.0\n"
                    f"ref-p = {rp}\ncompressibility = 4.5e-5\n"
                    "pbc = xyz\ncutoff-scheme = Verlet\nns_type = grid\n"
                    "coulombtype = PME\nrcoulomb = 1.0\nrvdw = 1.0\nDispCorr = EnerPres\n"
                    "constraints = h-bonds\nconstraint-algorithm = LINCS\n"
                    "continuation = yes\ngen-vel = no\n")
        self.btn.setEnabled(False)
        self._go(["grompp","-f","npt.mdp","-c","nvt.gro","-r","nvt.gro","-p","topol.top","-o","npt.tpr","-maxwarn","2"],
                 on_finish=lambda s,m: self._on_g(s,m))
    def _on_g(self, s, m):
        if not s: self.btn.setEnabled(True); QMessageBox.critical(self,"错误",f"NPT grompp: {m}"); return
        self._go(["mdrun","-deffnm","npt","-v"], on_finish=lambda s2,m2: self._done(s2,m2))
    def _done(self, s, m):
        self.btn.setEnabled(True)
        if s: self.main_window.log(">>> ✓ NPT"); self.npt_done.emit(self.cwd)
        else: QMessageBox.critical(self,"错误",f"NPT: {m}")
    def _go(self, args, input_text=None, on_finish=None):
        w = self.runner.create_worker(args, cwd=self.cwd, input_text=input_text)
        w.output_signal.connect(self.main_window.log)
        if on_finish: w.finished_signal.connect(on_finish); w.start()
