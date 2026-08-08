from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QGroupBox, 
                             QFormLayout, QComboBox, QLineEdit, 
                             QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt
import os
import sys
import re

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
        self._group_cache = {}  # cwd -> {name: number}

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
            warn_label.setStyleSheet("color: #f48771;")
            layout.addWidget(warn_label)

    def get_cwd(self):
        try:
            current_idx = self.main_window.stacked_widget.currentIndex()
            if current_idx == 0: # Solution Simulator
                return self.main_window.solution_tabs.widget(0).cwd
            elif current_idx == 1: # Ligand Simulator
                return self.main_window.ligand_simulator.prep_tab.cwd
        except:
            pass
        return None

    def set_buttons_enabled(self, enabled):
        for child in self.findChildren(QPushButton):
            child.setEnabled(enabled)

    # --- 动态索引组检测 ---

    def _get_group_map(self, cwd):
        """
        通过 gmx make_ndx 获取指定工作目录下体系的索引组名→编号映射。
        结果按 cwd 缓存，仅首次调用时执行命令。
        返回 dict: {"System": 0, "Protein": 1, "Backbone": 4, ...}
        失败时返回空 dict。
        """
        if cwd in self._group_cache:
            return self._group_cache[cwd]

        # 尝试多个可能的结构文件作为 make_ndx 的输入
        candidates = ["md_0_1.tpr", "npt.tpr", "em.tpr", "topol.tpr"]
        tpr_file = None
        for name in candidates:
            if os.path.exists(os.path.join(cwd, name)):
                tpr_file = name
                break

        if not tpr_file:
            self.main_window.log("[分析] 未找到 .tpr 文件，无法自动检测索引组，将使用默认编号。")
            self._group_cache[cwd] = {}
            return {}

        self.main_window.log(f"[分析] 正在检测体系索引组 (基于 {tpr_file})...")
        success, output = self.runner.run_command(
            ["make_ndx", "-f", tpr_file, "-o", "dummy.ndx"],
            cwd=cwd,
            input_text="q\n"
        )

        groups = {}
        if success and output:
            for line in output.split('\n'):
                m = re.match(r'^\s*(\d+)\s+(\S+)\s*:', line)
                if m:
                    groups[m.group(2)] = int(m.group(1))

        if groups:
            self.main_window.log(f"[分析] 检测到 {len(groups)} 个索引组。")
        else:
            self.main_window.log("[分析] 未能解析索引组列表，将使用默认编号。")

        # 清理 make_ndx 生成的临时文件
        dummy = os.path.join(cwd, "dummy.ndx")
        if os.path.exists(dummy):
            try:
                os.remove(dummy)
            except OSError:
                pass

        self._group_cache[cwd] = groups
        return groups

    def _resolve_group(self, cwd, preferred_names, fallback_number):
        """
        根据优选名称列表查找组号，找不到则返回 fallback_number。
        preferred_names: 按优先级排列的组名列表，如 ["Backbone", "MainChain"]
        """
        groups = self._get_group_map(cwd)
        for name in preferred_names:
            if name in groups:
                self.main_window.log(f"[分析] 自动匹配组: '{name}' -> #{groups[name]}")
                return groups[name]
        self.main_window.log(f"[分析] 未找到优选组 {preferred_names}，使用默认编号: #{fallback_number}")
        return fallback_number

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
        # 动态检测组号，找不到则使用默认值
        
        protein_num = self._resolve_group(cwd, ["Protein", "Protein-H"], 1)
        system_num = self._resolve_group(cwd, ["System"], 0)
        input_str = f"{protein_num}\n{system_num}\n" if center else f"{system_num}\n"
        
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
        # RMSD: 两个组选择（拟合组 + 计算组），通常都选 Backbone
        self._run_analysis("rms", "rmsd.xvg",
                           [(["Backbone", "MainChain"], 4), (["Backbone", "MainChain"], 4)],
                           "RMSD (Backbone)")

    def run_rmsf(self):
        # RMSF: 单个组选择，Protein 或 C-alpha
        self._run_analysis("rmsf", "rmsf.xvg",
                           [(["Protein", "C-alpha"], 1)],
                           "RMSF")

    def run_gyrate(self):
        # Gyrate: 单个组选择，Protein
        self._run_analysis("gyrate", "gyrate.xvg",
                           [(["Protein"], 1)],
                           "回转半径")

    def _run_analysis(self, tool, output_file, group_specs, desc):
        """
        执行 GROMACS 分析命令。
        group_specs: [(preferred_names_list, fallback_num), ...]
                     每个元素对应一个组选择提示符。
        """
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

        # 动态解析组号
        input_parts = []
        for preferred_names, fallback_num in group_specs:
            num = self._resolve_group(cwd, preferred_names, fallback_num)
            input_parts.append(str(num))
        input_group = "\n".join(input_parts) + "\n"
            
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

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(lambda: self.save_plot(fig, filename, cwd))
        plot_layout.addWidget(btn_save)

        self.plot_window.show()

    def save_plot(self, fig, source_filename, cwd):
        default_name = os.path.splitext(source_filename)[0] + ".png"
        default_path = os.path.join(cwd, default_name)

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存图片",
            default_path,
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg)"
        )

        if not save_path:
            return

        try:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")
            self.main_window.log(f"已保存图像: {save_path}")
            QMessageBox.information(self, "成功", f"图像已保存到:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存图像失败: {str(e)}")

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
