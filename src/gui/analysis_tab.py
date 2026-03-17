from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QComboBox, QLineEdit, 
                             QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt
import os
import sys

# 尝试导入 matplotlib，如果失败则禁用绘图功能
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

class AnalysisTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # === 1. 轨迹处理 (trjconv) ===
        trj_group = QGroupBox("1. 轨迹处理 (去除周期性边界条件)")
        trj_layout = QFormLayout()
        
        self.trj_input = QLineEdit("md_0_1.xtc")
        self.trj_tpr = QLineEdit("md_0_1.tpr")
        self.trj_output = QLineEdit("md_noPBC.xtc")
        
        self.pbc_combo = QComboBox()
        self.pbc_combo.addItems(["mol", "res", "atom", "no", "cluster"])
        self.pbc_combo.setCurrentText("mol")
        
        self.center_check = QComboBox()
        self.center_check.addItems(["yes", "no"]) # -center flag
        self.center_check.setCurrentText("yes")
        
        btn_trjconv = QPushButton("运行 trjconv")
        btn_trjconv.clicked.connect(self.run_trjconv)
        
        trj_layout.addRow("输入轨迹 (-f):", self.trj_input)
        trj_layout.addRow("输入 TPR (-s):", self.trj_tpr)
        trj_layout.addRow("输出轨迹 (-o):", self.trj_output)
        trj_layout.addRow("PBC 处理 (-pbc):", self.pbc_combo)
        trj_layout.addRow("居中 (-center):", self.center_check)
        trj_layout.addRow("", btn_trjconv)
        
        trj_group.setLayout(trj_layout)
        layout.addWidget(trj_group)
        
        # === 2. 数据分析 (RMSD, RMSF, Gyrate) ===
        ana_group = QGroupBox("2. 数据分析")
        ana_layout = QVBoxLayout()
        
        # RMSD
        rmsd_layout = QHBoxLayout()
        btn_rmsd = QPushButton("计算 RMSD (gmx rms)")
        btn_rmsd.clicked.connect(self.run_rmsd)
        btn_plot_rmsd = QPushButton("绘图 RMSD")
        btn_plot_rmsd.clicked.connect(lambda: self.plot_xvg("rmsd.xvg", "RMSD", "Time (ps)", "RMSD (nm)"))
        rmsd_layout.addWidget(btn_rmsd)
        rmsd_layout.addWidget(btn_plot_rmsd)
        ana_layout.addLayout(rmsd_layout)
        
        # RMSF
        rmsf_layout = QHBoxLayout()
        btn_rmsf = QPushButton("计算 RMSF (gmx rmsf)")
        btn_rmsf.clicked.connect(self.run_rmsf)
        btn_plot_rmsf = QPushButton("绘图 RMSF")
        btn_plot_rmsf.clicked.connect(lambda: self.plot_xvg("rmsf.xvg", "RMSF", "Residue", "RMSF (nm)"))
        rmsf_layout.addWidget(btn_rmsf)
        rmsf_layout.addWidget(btn_plot_rmsf)
        ana_layout.addLayout(rmsf_layout)
        
        # Gyrate
        gyrate_layout = QHBoxLayout()
        btn_gyrate = QPushButton("计算回转半径 (gmx gyrate)")
        btn_gyrate.clicked.connect(self.run_gyrate)
        btn_plot_gyrate = QPushButton("绘图 Gyrate")
        btn_plot_gyrate.clicked.connect(lambda: self.plot_xvg("gyrate.xvg", "Radius of Gyration", "Time (ps)", "Rg (nm)"))
        gyrate_layout.addWidget(btn_gyrate)
        gyrate_layout.addWidget(btn_plot_gyrate)
        ana_layout.addLayout(gyrate_layout)

        ana_group.setLayout(ana_layout)
        layout.addWidget(ana_group)
        
        # === 3. 可视化集成 ===
        vis_group = QGroupBox("3. 外部可视化工具")
        vis_layout = QHBoxLayout()
        
        btn_vmd = QPushButton("尝试启动 VMD")
        btn_vmd.clicked.connect(self.launch_vmd)
        
        btn_pymol = QPushButton("尝试启动 PyMOL")
        btn_pymol.clicked.connect(self.launch_pymol)
        
        vis_layout.addWidget(btn_vmd)
        vis_layout.addWidget(btn_pymol)
        
        vis_group.setLayout(vis_layout)
        layout.addWidget(vis_group)

        if not HAS_MATPLOTLIB:
            warn_label = QLabel("提示: 未检测到 matplotlib，绘图功能不可用。请运行 pip install matplotlib")
            warn_label.setStyleSheet("color: red;")
            layout.addWidget(warn_label)

    def get_cwd(self):
        try:
            topo_tab = self.main_window.tabs.widget(0)
            return topo_tab.cwd
        except:
            return None

    def set_buttons_enabled(self, enabled):
        for child in self.findChildren(QPushButton):
            child.setEnabled(enabled)

    # --- 运行逻辑 ---

    def run_trjconv(self):
        cwd = self.get_cwd()
        if not cwd: return
        
        trj_in = self.trj_input.text()
        tpr_in = self.trj_tpr.text()
        trj_out = self.trj_output.text()
        pbc = self.pbc_combo.currentText()
        center = self.center_check.currentText() == "yes"
        
        if not os.path.exists(os.path.join(cwd, trj_in)):
            QMessageBox.warning(self, "警告", f"未找到输入轨迹: {trj_in}")
            return
            
        args = ["trjconv", "-s", tpr_in, "-f", trj_in, "-o", trj_out, "-pbc", pbc]
        if center:
            args.append("-center")
            
        # trjconv 需要选择组 (通常选 Protein 用于居中，System 用于输出)
        # 如果启用了 center，需要两次输入 (1: Protein, 0: System)
        # 如果没启用 center，通常只需要一次输入 (0: System)
        
        input_str = "1\n0\n" if center else "0\n" 
        
        self.worker_trj = self.runner.create_worker(args, cwd=cwd, input_text=input_str)
        self.worker_trj.output_signal.connect(self.main_window.log)
        self.worker_trj.finished_signal.connect(self.on_trj_finished)
        
        self.set_buttons_enabled(False)
        self.worker_trj.start()
        
    def on_trj_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "成功", f"轨迹处理完成！输出文件: {self.trj_output.text()}")
        else:
            QMessageBox.critical(self, "错误", f"trjconv 失败: {message}")

    def run_rmsd(self):
        self._run_analysis("rms", "rmsd.xvg", "4\n4\n", "计算 RMSD (Backbone)") # 4=Backbone

    def run_rmsf(self):
        self._run_analysis("rmsf", "rmsf.xvg", "1\n", "计算 RMSF (Protein)") # 1=Protein

    def run_gyrate(self):
        self._run_analysis("gyrate", "gyrate.xvg", "1\n", "计算回转半径 (Protein)") # 1=Protein

    def _run_analysis(self, tool, output_file, input_group, desc):
        cwd = self.get_cwd()
        if not cwd: return
        
        # 优先使用处理过的轨迹，如果没有则使用原始轨迹
        trj_file = "md_noPBC.xtc"
        if not os.path.exists(os.path.join(cwd, trj_file)):
            trj_file = "md_0_1.xtc"
            
        if not os.path.exists(os.path.join(cwd, trj_file)):
             QMessageBox.warning(self, "警告", f"未找到轨迹文件 ({trj_file})，请先运行模拟或轨迹处理！")
             return

        args = [tool, "-s", "md_0_1.tpr", "-f", trj_file, "-o", output_file]
        
        # rmsf 需要 -res 标志来计算残基平均
        if tool == "rmsf":
            args.append("-res")
            
        self.worker_ana = self.runner.create_worker(args, cwd=cwd, input_text=input_group)
        self.worker_ana.output_signal.connect(self.main_window.log)
        
        # 使用闭包或偏函数传递额外信息
        self.worker_ana.finished_signal.connect(lambda s, m: self.on_analysis_finished(s, m, desc, output_file))
        
        self.set_buttons_enabled(False)
        self.worker_ana.start()

    def on_analysis_finished(self, success, message, desc, output_file):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "成功", f"{desc} 完成！生成了 {output_file}")
        else:
            QMessageBox.critical(self, "错误", f"{desc} 失败: {message}")

    # --- 绘图逻辑 ---
    
    def plot_xvg(self, filename, title, xlabel, ylabel):
        if not HAS_MATPLOTLIB:
            QMessageBox.warning(self, "警告", "未安装 matplotlib，无法绘图。")
            return
            
        cwd = self.get_cwd()
        if not cwd: return
        
        filepath = os.path.join(cwd, filename)
        if not os.path.exists(filepath):
            QMessageBox.warning(self, "警告", f"未找到数据文件: {filename}\n请先运行相应的分析命令。")
            return
            
        x, y = [], []
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    if line.startswith(('#', '@')):
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        x.append(float(parts[0]))
                        y.append(float(parts[1]))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取文件失败: {str(e)}")
            return
            
        if not x:
            QMessageBox.warning(self, "警告", "数据文件为空或格式无法解析。")
            return

        # 创建绘图窗口
        self.plot_window = QWidget()
        self.plot_window.setWindowTitle(f"Plot: {title}")
        self.plot_window.resize(600, 400)
        plot_layout = QVBoxLayout(self.plot_window)
        
        fig = Figure(figsize=(5, 4), dpi=100)
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.plot(x, y)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(True)
        
        plot_layout.addWidget(canvas)
        self.plot_window.show()

    # --- 可视化启动 ---
    
    def launch_vmd(self):
        self._launch_vis_tool("vmd")

    def launch_pymol(self):
        self._launch_vis_tool("pymol")
        
    def _launch_vis_tool(self, tool_name):
        cwd = self.get_cwd()
        if not cwd: return
        
        gro = "npt.gro" # 使用 NPT 后的结构作为拓扑参考
        xtc = "md_noPBC.xtc" # 优先使用处理过的轨迹
        if not os.path.exists(os.path.join(cwd, xtc)):
            xtc = "md_0_1.xtc"
            
        # 简单的启动命令
        # 注意：这假设工具在系统 PATH 中。如果不在，可能需要配置路径。
        import subprocess
        try:
            cmd = [tool_name]
            if tool_name == "vmd":
                if os.path.exists(os.path.join(cwd, gro)): cmd.extend([gro])
                if os.path.exists(os.path.join(cwd, xtc)): cmd.extend([xtc])
            elif tool_name == "pymol":
                 if os.path.exists(os.path.join(cwd, gro)): cmd.extend([gro])
                 if os.path.exists(os.path.join(cwd, xtc)): cmd.extend([xtc])
            
            subprocess.Popen(cmd, cwd=cwd)
            self.main_window.log(f">>> 正在启动 {tool_name}...")
        except FileNotFoundError:
             QMessageBox.warning(self, "警告", f"未找到 {tool_name} 命令。请确保它已安装并添加到系统 PATH 中。")
        except Exception as e:
             QMessageBox.critical(self, "错误", f"启动 {tool_name} 失败: {str(e)}")
