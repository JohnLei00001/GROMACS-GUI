from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGroupBox, QFileDialog,
                             QFormLayout, QComboBox, QLineEdit, 
                             QMessageBox, QScrollArea, QFrame)
import os
from gui.mdp_panel import MDPPanel

class EMTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.init_ui()

    def init_ui(self):
        # 滚动容器：内容超高时允许滚动，避免窗口拉矮后被裁切
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget(); layout = QVBoxLayout(w)

        # 1. MDP 参数面板
        mdp_group = QGroupBox("1. 准备能量最小化参数 (minim.mdp)")
        mdp_l = QVBoxLayout()
        self.mdp_panel = MDPPanel("em")
        btn_row = QHBoxLayout()
        btn_save = QPushButton("保存为 minim.mdp")
        btn_save.clicked.connect(self.save_mdp)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        mdp_l.addWidget(self.mdp_panel)
        mdp_l.addLayout(btn_row)
        mdp_group.setLayout(mdp_l)
        layout.addWidget(mdp_group)

        # 2. GROMPP
        grompp_group = QGroupBox("2. 生成运行文件 (grompp)")
        grompp_l = QFormLayout()
        btn_run_grompp = QPushButton("运行 grompp")
        btn_run_grompp.clicked.connect(self.run_grompp)
        grompp_l.addRow("执行预处理:", btn_run_grompp)
        grompp_group.setLayout(grompp_l)
        layout.addWidget(grompp_group)

        # 3. MDRUN
        mdrun_group = QGroupBox("3. 执行能量最小化 (mdrun)")
        mdrun_l = QFormLayout()
        self.gpu_check = QComboBox()
        self.gpu_check.addItems(["自动检测", "强制使用 GPU", "仅使用 CPU"])
        mdrun_l.addRow("硬件加速:", self.gpu_check)
        btn_run_mdrun = QPushButton("运行 mdrun")
        btn_run_mdrun.clicked.connect(self.run_mdrun)
        mdrun_l.addRow("执行计算:", btn_run_mdrun)
        mdrun_group.setLayout(mdrun_l)
        layout.addWidget(mdrun_group)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    def get_cwd(self):
        try:
            current_idx = self.main_window.stacked_widget.currentIndex()
            if current_idx == 0:
                return self.main_window.solution_tabs.widget(0).cwd
            elif current_idx == 1:
                return self.main_window.ligand_simulator.prep_tab.cwd
        except:
            pass
        return None

    def save_mdp(self):
        cwd = self.get_cwd()
        if not cwd:
            QMessageBox.warning(self, "警告", "请先在'拓扑与水箱'步骤中选择文件以确定工作目录！")
            return
        try:
            with open(os.path.join(cwd, "minim.mdp"), "w") as f:
                f.write(self.mdp_panel.get_mdp_text())
            self.main_window.log(f"已保存 minim.mdp → {cwd}")
            QMessageBox.information(self, "成功", "minim.mdp 已保存。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def run_grompp(self):
        cwd = self.get_cwd()
        if not cwd: return
        input_gro = None
        for c in ["complex_solv_ions.gro", "solvated_ions.gro", "complex_solv.gro", "solvated.gro", "processed.gro"]:
            if os.path.exists(os.path.join(cwd, c)):
                input_gro = c; break
        if not input_gro:
            QMessageBox.warning(self, "警告", "未找到输入结构文件，请确保已完成之前的步骤。"); return
        for f in ["minim.mdp", "topol.top"]:
            if not os.path.exists(os.path.join(cwd, f)):
                QMessageBox.warning(self, "警告", f"缺少必要文件: {f}"); return
        args = ["grompp", "-f", "minim.mdp", "-c", input_gro, "-p", "topol.top", "-o", "em.tpr", "-maxwarn", "1"]
        self.main_window.log(f"\n>>> 正在运行: gmx {' '.join(args)}")
        self.worker = self.runner.create_worker(args, cwd=cwd)
        self.worker.output_signal.connect(self.main_window.log)
        self.worker.finished_signal.connect(self.on_grompp_finished)
        self._set_btns(False)
        self.worker.start()

    def on_grompp_finished(self, success, message):
        self._set_btns(True)
        if success:
            QMessageBox.information(self, "成功", "grompp 完成！生成了 em.tpr")
        else:
            QMessageBox.critical(self, "错误", f"grompp 失败: {message}")

    def run_mdrun(self):
        cwd = self.get_cwd()
        if not cwd or not os.path.exists(os.path.join(cwd, "em.tpr")):
            QMessageBox.warning(self, "警告", "未找到 em.tpr，请先运行 grompp！"); return
        args = ["mdrun", "-v", "-deffnm", "em"]
        gpu = self.gpu_check.currentText()
        if gpu == "强制使用 GPU": args.extend(["-nb", "gpu"])
        elif gpu == "仅使用 CPU": args.extend(["-nb", "cpu"])
        self.main_window.log(f"\n>>> 正在运行: gmx {' '.join(args)}")
        self.worker = self.runner.create_worker(args, cwd=cwd)
        self.worker.output_signal.connect(self.main_window.log)
        self.worker.finished_signal.connect(self.on_mdrun_finished)
        self._set_btns(False)
        self.worker.start()

    def on_mdrun_finished(self, success, message):
        self._set_btns(True)
        if success:
            QMessageBox.information(self, "成功", "EM 能量最小化完成！")
        else:
            QMessageBox.critical(self, "错误", f"mdrun (EM) 失败: {message}")

    def _set_btns(self, enabled):
        for child in self.findChildren(QPushButton): child.setEnabled(enabled)
