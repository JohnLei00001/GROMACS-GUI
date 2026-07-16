from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QPushButton, QLabel, QGroupBox, 
                             QProgressBar, QListWidget, QListWidgetItem,
                             QMessageBox, QCheckBox)
from PyQt6.QtCore import pyqtSignal, QTimer
import os

class BatchTab(QWidget):
    """批量执行伞形窗口 MD"""

    batch_done = pyqtSignal(str)  # (cwd)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.runner = main_window.runner
        self.cwd = ""
        self.windows = []
        self.current_index = 0
        self.running = False
        self.init_ui()

    def init_ui(self):
        root = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        w = QWidget(); layout = QVBoxLayout(w)

        self.status_label = QLabel("等待窗口配置完成...")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.status_label)

        # 控制
        ctrl = QHBoxLayout()
        self.chk_skip_done = QCheckBox("跳过已完成窗口")
        self.chk_skip_done.setChecked(True)
        ctrl.addWidget(self.chk_skip_done)

        self.btn_run = QPushButton("▶ 开始批量 MD")
        self.btn_run.clicked.connect(self.start_batch)
        ctrl.addWidget(self.btn_run)

        self.btn_stop = QPushButton("⏹ 停止")
        self.btn_stop.clicked.connect(self.stop_batch)
        self.btn_stop.setEnabled(False)
        ctrl.addWidget(self.btn_stop)
        layout.addLayout(ctrl)

        # 进度条
        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        # 窗口列表（显示完成状态）
        g = QGroupBox("窗口状态")
        gl = QVBoxLayout()
        self.win_list = QListWidget()
        gl.addWidget(self.win_list)
        g.setLayout(gl)
        layout.addWidget(g)

        layout.addStretch()
        scroll.setWidget(w); root.addWidget(scroll)

    def update_windows(self, cwd, windows):
        self.cwd = cwd
        self.windows = windows
        self.status_label.setText(f"✅ {len(windows)} 个窗口已就绪 (目录: {cwd})")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        self._refresh_list()

    def _refresh_list(self):
        self.win_list.clear()
        for i, (frame_d, ref_d, dir_name) in enumerate(self.windows):
            done = os.path.exists(os.path.join(self.cwd, dir_name, "umbrella.gro"))
            status = "✅" if done else "⏳"
            item = QListWidgetItem(f"  [{i:3d}] {dir_name}  ref={ref_d:.3f} nm  {status}")
            self.win_list.addItem(item)

    def start_batch(self):
        if not self.windows or not self.cwd:
            return

        self.running = True
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.current_index = 0
        self.progress.setMaximum(len(self.windows))
        self._run_next()

    def stop_batch(self):
        self.running = False
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.main_window.log(">>> 批量 MD 已停止")

    def _run_next(self):
        if not self.running:
            return
        if self.current_index >= len(self.windows):
            self._all_done()
            return

        _, ref_d, dir_name = self.windows[self.current_index]
        win_dir = os.path.join(self.cwd, dir_name)

        # 跳过已完成
        if self.chk_skip_done.isChecked() and os.path.exists(os.path.join(win_dir, "umbrella.gro")):
            self.main_window.log(f">>> [{self.current_index+1}/{len(self.windows)}] 跳过 {dir_name} (已完成)")
            self.current_index += 1
            self._refresh_list()
            self.progress.setValue(self.current_index)
            self._run_next()
            return

        self.main_window.log(f">>> [{self.current_index+1}/{len(self.windows)}] 运行 {dir_name} (ref={ref_d:.3f} nm)")

        # grompp
        a1 = ["grompp", "-f", "umbrella.mdp", "-c", "npt.gro", "-p", "topol.top", "-o", "umbrella.tpr", "-maxwarn", "2"]
        w1 = self.runner.create_worker(a1, cwd=win_dir)
        w1.output_signal.connect(self.main_window.log)
        w1.finished_signal.connect(lambda s, m: self._on_grompp_done(s, m, win_dir))
        w1.start()

    def _on_grompp_done(self, success, message, win_dir):
        if not success:
            self.main_window.log(f"  ✗ grompp 失败: {message[:200]}")
            self.current_index += 1
            self.progress.setValue(self.current_index)
            self._refresh_list()
            self._run_next()
            return

        w2 = self.runner.create_worker(["mdrun", "-deffnm", "umbrella", "-v"], cwd=win_dir)
        w2.output_signal.connect(self.main_window.log)
        w2.finished_signal.connect(lambda s, m: self._on_window_done(s, m, win_dir))
        w2.start()

    def _on_window_done(self, success, message, win_dir):
        name = os.path.basename(win_dir)
        if success:
            self.main_window.log(f"  ✓ {name} 完成")
        else:
            self.main_window.log(f"  ✗ {name} 失败: {message[:200]}")
        self.current_index += 1
        self.progress.setValue(self.current_index)
        self._refresh_list()
        self._run_next()

    def _all_done(self):
        self.running = False
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._refresh_list()
        done_count = sum(1 for _, _, dn in self.windows if os.path.exists(os.path.join(self.cwd, dn, "umbrella.gro")))
        self.main_window.log(f">>> ✓ 批量 MD 完成 ({done_count}/{len(self.windows)} 窗口成功)")
        QMessageBox.information(self, "完成", f"批量 MD 完成！\n{done_count}/{len(self.windows)} 窗口成功。\n请继续到「WHAM 分析」标签页。")
        self.batch_done.emit(self.cwd)
