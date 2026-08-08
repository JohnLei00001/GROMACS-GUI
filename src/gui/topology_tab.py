from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog,
                             QLineEdit, QCheckBox, QMessageBox, QComboBox,
                             QFormLayout, QScrollArea, QFrame)
import os

from gui.i18n import tr, trf
from gui.widgets import StepCard
from gui.theme import set_role

FALLBACK_FORCEFIELDS = ["amber03", "amber94", "amber96", "amber99", "amber99sb",
                        "amber99sb-ildn", "charmm27", "charmm36-jul2022", "oplsaa"]

def discover_forcefields():
    """从 GMXLIB 目录自动发现可用力场"""
    from core.config import get_gmx_top_dir
    gmx_top_dir = get_gmx_top_dir()
    if gmx_top_dir:
        discovered = []
        for name in sorted(os.listdir(gmx_top_dir)):
            if name.endswith('.ff') and os.path.isdir(os.path.join(gmx_top_dir, name)):
                discovered.append(name[:-3])
        if discovered:
            return discovered
    return FALLBACK_FORCEFIELDS

# pdb2gmx 不认识的残基名（水、常见离子），需在运行前自动剥离
PDB_STRIP_RESIDUES = {"HOH", "WAT", "SOL", "TIP", "TIP3", "NA", "CL", "K",
                       "CA", "MG", "ZN", "FE", "MN", "SO4", "PO4"}

def strip_pdb_nonprotein(pdb_path):
    """自动去除 PDB 中 pdb2gmx 不认识的水分子和离子，返回清理后的内容"""
    with open(pdb_path, 'r') as f:
        lines = f.readlines()
    stripped = []
    removed = 0
    for line in lines:
        if line.startswith("ATOM") or line.startswith("HETATM"):
            resname = line[17:20].strip()
            if resname in PDB_STRIP_RESIDUES:
                removed += 1
                continue
        stripped.append(line)
    if removed > 0:
        with open(pdb_path, 'w') as f:
            f.writelines(stripped)
    return removed

class TopologyTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window # Reference to main window for logging and running
        self.runner = main_window.runner
        self.cwd = ""  # 由用户选择输入文件或手动指定工作目录

        self.init_ui()

    def init_ui(self):
        # 滚动容器：内容超高时允许滚动，避免窗口拉矮后被裁切
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        w = QWidget(); layout = QVBoxLayout(w)
        layout.setSpacing(10)

        # 0. 工作目录设置
        dir_card = StepCard(0, tr("设置工作目录"), layout_kind="vbox")
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit(self.cwd)
        self.dir_input.setPlaceholderText(tr("选择输入文件后将自动使用其所在目录"))
        btn_browse_dir = QPushButton(tr("浏览..."))
        btn_browse_dir.clicked.connect(self.browse_dir)
        dir_layout.addWidget(QLabel(tr("工作目录:")))
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(btn_browse_dir)
        dir_card.content_layout.addLayout(dir_layout)
        layout.addWidget(dir_card)

        # 1. 基础测试与环境
        test_card = StepCard(1, tr("基础测试与环境"), layout_kind="vbox")
        test_layout = QHBoxLayout()
        test_btn = QPushButton(tr("测试 GROMACS 安装 (gmx -version)"))
        test_btn.clicked.connect(self.main_window.test_gmx)
        set_role(test_btn, "primary")
        test_layout.addWidget(test_btn)
        test_card.content_layout.addLayout(test_layout)
        layout.addWidget(test_card)

        # 1. PDB2GMX 区块
        pdb_card = StepCard(1, tr("生成拓扑 (pdb2gmx)"), layout_kind="form")
        pdb_layout = pdb_card.content_layout

        # 输入文件选择
        file_layout = QHBoxLayout()
        self.pdb_input = QLineEdit()
        self.pdb_input.setPlaceholderText(tr("选择输入的 .pdb 文件..."))
        btn_browse = QPushButton(tr("浏览..."))
        btn_browse.clicked.connect(self.browse_pdb)
        file_layout.addWidget(self.pdb_input)
        file_layout.addWidget(btn_browse)
        pdb_layout.addRow(tr("输入 PDB:"), file_layout)

        # 力场选择
        self.ff_combo = QComboBox()
        # 常见力场选项
        self.ff_combo.addItems(discover_forcefields())
        self.ff_combo.setCurrentText("oplsaa")
        pdb_layout.addRow(tr("力场 (-ff):"), self.ff_combo)

        # 水模型选择
        self.water_combo = QComboBox()
        self.water_combo.addItems(["spce", "tip3p", "tip4p", "tip5p"])
        self.water_combo.setCurrentText("spce")
        pdb_layout.addRow(tr("水模型 (-water):"), self.water_combo)

        # 忽略氢原子
        self.ignh_check = QCheckBox(tr("忽略输入文件中的氢原子 (-ignh)"))
        self.ignh_check.setChecked(True)
        pdb_layout.addRow("", self.ignh_check)

        # 执行按钮
        btn_run_pdb2gmx = QPushButton(tr("运行 pdb2gmx"))
        btn_run_pdb2gmx.clicked.connect(self.run_pdb2gmx)
        set_role(btn_run_pdb2gmx, "primary")
        pdb_layout.addRow("", btn_run_pdb2gmx)

        layout.addWidget(pdb_card)

        # 2. EDITCONF 区块 (定义盒子)
        box_card = StepCard(2, tr("定义盒子 (editconf)"), layout_kind="form")
        box_layout = box_card.content_layout

        self.box_type = QComboBox()
        self.box_type.addItems(["cubic", "triclinic", "dodecahedron", "octahedron"])
        self.box_type.setCurrentText("cubic")
        box_layout.addRow(tr("盒子形状 (-bt):"), self.box_type)

        self.box_dist = QLineEdit("1.0")
        box_layout.addRow(tr("边缘距离 (-d, nm):"), self.box_dist)

        btn_run_editconf = QPushButton(tr("运行 editconf"))
        btn_run_editconf.clicked.connect(self.run_editconf)
        set_role(btn_run_editconf, "primary")
        box_layout.addRow("", btn_run_editconf)

        layout.addWidget(box_card)

        # 3. SOLVATE 区块 (添加溶剂)
        solvate_card = StepCard(3, tr("添加溶剂 (solvate)"), layout_kind="form")
        solvate_layout = solvate_card.content_layout

        btn_run_solvate = QPushButton(tr("运行 solvate"))
        btn_run_solvate.clicked.connect(self.run_solvate)
        set_role(btn_run_solvate, "primary")
        solvate_layout.addRow("", btn_run_solvate)

        layout.addWidget(solvate_card)

        # 4. GENION 区块 (添加离子)
        genion_card = StepCard(4, tr("添加离子中和系统 (genion)"), layout_kind="form")
        genion_layout = genion_card.content_layout

        # 为了运行 genion，我们需要先运行一个只生成 tpr 的 grompp
        # 所以我提供一个一键按钮：先 grompp 生成 ions.tpr，再 genion
        self.pname_input = QLineEdit("NA")
        self.nname_input = QLineEdit("CL")
        self.conc_input = QLineEdit("0.15")
        self.neutral_check = QCheckBox(tr("自动中和系统电荷 (-neutral)"))
        self.neutral_check.setChecked(True)

        genion_layout.addRow(tr("阳离子名称 (-pname):"), self.pname_input)
        genion_layout.addRow(tr("阴离子名称 (-nname):"), self.nname_input)
        genion_layout.addRow(tr("盐浓度 (-conc, mol/L):"), self.conc_input)
        genion_layout.addRow("", self.neutral_check)

        btn_run_genion = QPushButton(tr("运行 genion (先 grompp 后 genion)"))
        btn_run_genion.clicked.connect(self.run_genion)
        set_role(btn_run_genion, "primary")
        genion_layout.addRow("", btn_run_genion)

        layout.addWidget(genion_card)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    def browse_pdb(self):
        start_dir = self.cwd or os.getcwd()
        file_path, _ = QFileDialog.getOpenFileName(self, tr("选择 PDB 文件"), start_dir, "PDB Files (*.pdb);;All Files (*)")
        if file_path:
            self.cwd = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            self.dir_input.setText(self.cwd)
            self.pdb_input.setText(file_name)
            self.main_window.log(trf("已选择输入文件: {file}", file=file_name))
            self.main_window.log(trf("工作目录已切换为输入文件所在目录: {dir}", dir=self.cwd))

    def browse_dir(self):
        start_dir = self.cwd or os.getcwd()
        d = QFileDialog.getExistingDirectory(self, tr("选择工作目录"), start_dir)
        if d:
            self.cwd = d
            self.dir_input.setText(d)

    def set_buttons_enabled(self, enabled):
        """启用或禁用所有按钮，防止重复提交任务"""
        for child in self.findChildren(QPushButton):
            child.setEnabled(enabled)

    def run_pdb2gmx(self):
        # 此时 self.pdb_input.text() 可能只有文件名 "protein.pdb"
        pdb_filename = self.pdb_input.text()

        # 拼接完整路径用于检查文件是否存在
        full_pdb_path = os.path.join(self.cwd, pdb_filename)

        if not pdb_filename or not os.path.exists(full_pdb_path):
            QMessageBox.warning(self, tr("警告"), trf("在工作目录中未找到文件: {file}", file=pdb_filename))
            return

        # 自动去除 PDB 中 pdb2gmx 不认识的水分子和离子
        removed = strip_pdb_nonprotein(full_pdb_path)
        if removed > 0:
            self.main_window.log(trf(">>> 自动清理: 从 PDB 中移除了 {n} 个非蛋白残基（水/离子）", n=removed))

        ff = self.ff_combo.currentText()
        water = self.water_combo.currentText()
        ignh = self.ignh_check.isChecked()

        # 构造命令时只使用文件名，因为 cwd 已经设置正确
        args = ["pdb2gmx", "-f", pdb_filename, "-o", "processed.gro", "-p", "topol.top", "-ff", ff, "-water", water, "-ter"]
        if ignh:
            args.append("-ignh")

        # -ter 交互式选择末端类型: 1=NH3+ (N端), 0=COO- (C端)
        self.worker_pdb2gmx = self.runner.create_worker(args, cwd=self.cwd, input_text="1\n0\n")
        self.worker_pdb2gmx.output_signal.connect(self.main_window.log)
        self.worker_pdb2gmx.finished_signal.connect(self.on_pdb2gmx_finished)

        self.set_buttons_enabled(False)
        self.worker_pdb2gmx.start()

    def on_pdb2gmx_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, tr("成功"), tr("pdb2gmx 运行完成！生成了 processed.gro 和 topol.top"))
        else:
            QMessageBox.critical(self, tr("错误"), trf("pdb2gmx 运行失败: {msg}", msg=message))

    def run_editconf(self):
        if not self.cwd:
            QMessageBox.warning(self, tr("警告"), tr("请先完成 pdb2gmx 步骤或设置工作目录！"))
            return

        gro_file = os.path.join(self.cwd, "processed.gro")
        if not os.path.exists(gro_file):
            QMessageBox.warning(self, tr("警告"), trf("未找到 processed.gro，请确保上一阶段已成功执行！\n期望路径: {path}", path=gro_file))
            return

        bt = self.box_type.currentText()
        d = self.box_dist.text()

        args = ["editconf", "-f", "processed.gro", "-o", "newbox.gro", "-c", "-d", d, "-bt", bt]

        # 使用异步 Worker 执行
        self.worker_editconf = self.runner.create_worker(args, cwd=self.cwd)
        self.worker_editconf.output_signal.connect(self.main_window.log)
        self.worker_editconf.finished_signal.connect(self.on_editconf_finished)

        self.set_buttons_enabled(False)
        self.worker_editconf.start()

    def on_editconf_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, tr("成功"), tr("editconf 运行完成！生成了 newbox.gro"))
        else:
            QMessageBox.critical(self, tr("错误"), trf("editconf 运行失败: {msg}", msg=message))

    def run_solvate(self):
        if not self.cwd:
            QMessageBox.warning(self, tr("警告"), tr("请先完成上述步骤或设置工作目录！"))
            return

        gro_file = os.path.join(self.cwd, "newbox.gro")
        top_file = os.path.join(self.cwd, "topol.top")

        if not os.path.exists(gro_file) or not os.path.exists(top_file):
            QMessageBox.warning(self, tr("警告"), tr("未找到 newbox.gro 或 topol.top，请确保上一阶段已成功执行！"))
            return

        # 根据用户选择的水模型自动匹配溶剂模板文件
        from core.config import get_solvent_template
        solvent = get_solvent_template(self.water_combo.currentText())
        self.main_window.log(trf("[溶剂化] 水模型: {model}, 溶剂模板: {tmpl}",
                                 model=self.water_combo.currentText(), tmpl=solvent))
        args = ["solvate", "-cp", "newbox.gro", "-cs", solvent, "-o", "solvated.gro", "-p", "topol.top"]

        # 使用异步 Worker 执行
        self.worker_solvate = self.runner.create_worker(args, cwd=self.cwd)
        self.worker_solvate.output_signal.connect(self.main_window.log)
        self.worker_solvate.finished_signal.connect(self.on_solvate_finished)

        self.set_buttons_enabled(False)
        self.worker_solvate.start()

    def on_solvate_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, tr("成功"), tr("solvate 运行完成！生成了 solvated.gro"))
        else:
            QMessageBox.critical(self, tr("错误"), trf("solvate 运行失败: {msg}", msg=message))

    def run_genion(self):
        if not self.cwd:
            QMessageBox.warning(self, tr("警告"), tr("请先完成上述步骤！"))
            return

        # 1. 首先需要生成一个离子的 mdp 文件 (最简单的即可)
        ions_mdp = os.path.join(self.cwd, "ions.mdp")
        if not os.path.exists(ions_mdp):
            try:
                with open(ions_mdp, "w") as f:
                    f.write("; ions.mdp - used as input into grompp to generate ions.tpr\n")
                    f.write("integrator  = steep\n")
                    f.write("emtol       = 1000.0\n")
                    f.write("emstep      = 0.01\n")
                    f.write("nsteps      = 50000\n")
                    f.write("nstlist         = 1\n")
                    f.write("cutoff-scheme   = Verlet\n")
                    f.write("ns_type         = grid\n")
                    f.write("coulombtype     = cutoff\n")
                    f.write("rcoulomb        = 1.0\n")
                    f.write("rvdw            = 1.0\n")
                    f.write("pbc             = xyz\n")
            except Exception as e:
                QMessageBox.critical(self, tr("错误"), trf("创建 ions.mdp 失败: {err}", err=str(e)))
                return

        # 2. 运行 grompp 生成 ions.tpr
        args_grompp = ["grompp", "-f", "ions.mdp", "-c", "solvated.gro", "-p", "topol.top", "-o", "ions.tpr"]
        # 忽略 maxwarn 防止刚才的报错打断离子生成
        args_grompp.append("-maxwarn")
        args_grompp.append("1")

        self.worker_genion_grompp = self.runner.create_worker(args_grompp, cwd=self.cwd)
        self.worker_genion_grompp.output_signal.connect(self.main_window.log)
        self.worker_genion_grompp.finished_signal.connect(self.on_genion_grompp_finished)

        self.set_buttons_enabled(False)
        self.worker_genion_grompp.start()

    def on_genion_grompp_finished(self, success, message):
        if not success:
            self.set_buttons_enabled(True)
            QMessageBox.critical(self, tr("错误"), trf("生成 ions.tpr 失败: {msg}", msg=message))
            return

        # 3. 运行 genion
        pname = self.pname_input.text()
        nname = self.nname_input.text()
        conc = self.conc_input.text()
        neutral = self.neutral_check.isChecked()

        args_genion = ["genion", "-s", "ions.tpr", "-o", "solvated_ions.gro", "-p", "topol.top",
                       "-pname", pname, "-nname", nname, "-conc", conc]
        if neutral:
            args_genion.append("-neutral")

        # 使用 input_text="SOL" 自动选择溶剂组
        self.worker_genion = self.runner.create_worker(args_genion, cwd=self.cwd, input_text="SOL")
        self.worker_genion.output_signal.connect(self.main_window.log)
        self.worker_genion.finished_signal.connect(self.on_genion_finished)

        self.worker_genion.start()

    def on_genion_finished(self, success, message):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, tr("成功"), tr("genion 运行完成！生成了 solvated_ions.gro，并已更新拓扑。"))
            QMessageBox.information(self, tr("注意"), tr("现在您已经添加了离子，后续的能量最小化请使用 [solvated_ions.gro] 作为输入！"))
        else:
            QMessageBox.critical(self, tr("错误"), trf("genion 运行失败: {msg}\n可能是找不到 'SOL' 组。", msg=message))
