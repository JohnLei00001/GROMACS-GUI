from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel, QGroupBox, QFormLayout,
                             QComboBox, QTextEdit, QMessageBox, QDialog)
from PyQt6.QtCore import pyqtSignal
from gui.mdp_editor import MDPEditor
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
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        w = QWidget(); layout = QVBoxLayout(w)

        self.status = QLabel("等待体系构建...")
        self.status.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.status)

        # 1. MDP 参数
        mdp_group = QGroupBox("1. 准备能量最小化参数 (minim.mdp)")
        mdp_l = QVBoxLayout()
        self.mdp_content = QTextEdit()
        self.mdp_content.setText(
            "; minim.mdp - used as input into grompp to generate em.tpr\n"
            "integrator  = steep         ; Algorithm (steep = steepest descent minimization)\n"
            "emtol       = 1000.0        ; Stop minimization when the maximum force < 1000.0 kJ/mol/nm\n"
            "emstep      = 0.01          ; Minimization step size\n"
            "nsteps      = 50000         ; Maximum number of (minimization) steps to perform\n"
            "\n"
            "; Parameters describing how to find the neighbors of each atom and how to calculate the interactions\n"
            "nstlist         = 1         ; Frequency to update the neighbor list and long range forces\n"
            "cutoff-scheme   = Verlet    ; Buffered neighbor searching\n"
            "ns_type         = grid      ; Method to determine neighbor list (simple, grid)\n"
            "coulombtype     = PME       ; Treatment of long range electrostatic interactions\n"
            "rcoulomb        = 1.0       ; Short-range electrostatic cut-off\n"
            "rvdw            = 1.0       ; Short-range Van der Waals cut-off\n"
            "pbc             = xyz       ; Periodic Boundary Conditions in all directions\n"
        )
        self.mdp_content.setStyleSheet("font-family: Consolas; font-size: 9pt;")
        btn_row = QHBoxLayout()
        btn_edit = QPushButton("打开参数编辑器")
        btn_edit.clicked.connect(self._open_editor)
        btn_save = QPushButton("保存为 minim.mdp")
        btn_save.clicked.connect(self._save_mdp)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_save)
        mdp_l.addWidget(self.mdp_content)
        mdp_l.addLayout(btn_row)
        mdp_group.setLayout(mdp_l)
        layout.addWidget(mdp_group)

        # 2. grompp
        grompp_group = QGroupBox("2. 生成运行文件 (grompp)")
        grompp_l = QFormLayout()
        self.btn_grompp = QPushButton("运行 grompp")
        self.btn_grompp.clicked.connect(self._run_grompp)
        grompp_l.addRow("执行预处理:", self.btn_grompp)
        grompp_group.setLayout(grompp_l)
        layout.addWidget(grompp_group)

        # 3. mdrun
        mdrun_group = QGroupBox("3. 执行能量最小化 (mdrun)")
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

    def _open_editor(self):
        dlg = MDPEditor(self, "em", self.mdp_content.toPlainText())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.mdp_content.setText(dlg.get_mdp_content())

    def _save_mdp(self):
        if not self.cwd:
            QMessageBox.warning(self, "警告", "请先完成体系构建")
            return
        try:
            with open(os.path.join(self.cwd, "minim.mdp"), "w") as f:
                f.write(self.mdp_content.toPlainText())
            self.main_window.log(f"已保存 minim.mdp → {self.cwd}")
            QMessageBox.information(self, "成功", "minim.mdp 已保存。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def _run_grompp(self):
        if not self.cwd: return
        for f in ["minim.mdp", "topol.top"]:
            if not os.path.exists(os.path.join(self.cwd, f)):
                QMessageBox.warning(self, "警告", f"缺少 {f}，请先完成体系构建"); return
        input_gro = None
        for c in ["solvated_ions.gro", "solvated.gro", "processed.gro"]:
            if os.path.exists(os.path.join(self.cwd, c)):
                input_gro = c; break
        if not input_gro:
            QMessageBox.warning(self, "警告", "未找到输入结构文件"); return
        self._set_btns(False)
        self._go(["grompp", "-f", "minim.mdp", "-c", input_gro, "-p", "topol.top", "-o", "em.tpr", "-maxwarn", "1"],
                 on_finish=lambda s, m: self._on_grompp_done(s, m))

    def _on_grompp_done(self, success, message):
        self._set_btns(True)
        if success:
            QMessageBox.information(self, "成功", "grompp 完成！已生成 em.tpr")
        else:
            QMessageBox.critical(self, "错误", f"grompp 失败: {message}")

    def _run_mdrun(self):
        if not self.cwd: return
        if not os.path.exists(os.path.join(self.cwd, "em.tpr")):
            QMessageBox.warning(self, "警告", "未找到 em.tpr，请先运行 grompp"); return
        args = ["mdrun", "-v", "-deffnm", "em"]
        gpu = self.gpu_combo.currentText()
        if gpu == "强制使用 GPU": args.extend(["-nb", "gpu"])
        elif gpu == "仅使用 CPU": args.extend(["-nb", "cpu"])
        self._set_btns(False)
        self._go(args, on_finish=lambda s, m: self._on_mdrun_done(s, m))

    def _on_mdrun_done(self, success, message):
        self._set_btns(True)
        if success:
            self.main_window.log(">>> ✓ EM 完成")
            QMessageBox.information(self, "成功", "EM 能量最小化完成！")
            self.em_done.emit(self.cwd)
        else:
            QMessageBox.critical(self, "错误", f"mdrun (EM) 失败: {message}")

    def _set_btns(self, enabled):
        for b in self.findChildren(QPushButton): b.setEnabled(enabled)

    def _go(self, args, input_text=None, on_finish=None):
        w = self.runner.create_worker(args, cwd=self.cwd, input_text=input_text)
        w.output_signal.connect(self.main_window.log)
        if on_finish: w.finished_signal.connect(on_finish)
        w.start()
