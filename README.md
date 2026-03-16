# GROMACS-GUI

这是一个基于 Python 和 PyQt6 开发的 GROMACS 图形用户界面 (GUI) 工具。旨在简化 GROMACS 分子动力学模拟的操作流程，提供可视化的参数配置和任务管理。

> **注意**: 本项目目前处于开发阶段 (Work In Progress)。

## ✨ 功能特性

目前支持以下主要流程：

1.  **拓扑与水箱 (Topology & Water Box)**
    *   生成拓扑文件
    *   定义溶剂盒子
2.  **能量最小化 (Energy Minimization)**
    *   配置 EM 参数
    *   运行能量最小化
3.  **系统平衡 (System Equilibration)**
    *   NVT/NPT 平衡模拟配置与运行

## 🛠️ 技术栈

*   **编程语言**: Python 3
*   **GUI 框架**: PyQt6
*   **后端引擎**: GROMACS (需要单独安装)

## 🚀 快速开始

### 前置要求

1.  **安装 Python**: 确保系统已安装 Python 3.8 或更高版本。
2.  **安装 GROMACS**: 本工具依赖 GROMACS 可执行文件 (`gmx` 或 `gmx_mpi`)。请确保已正确安装 GROMACS。

### 安装步骤

1.  克隆仓库：
    ```bash
    git clone https://github.com/JohnLei00001/GROMACS-GUI.git
    cd GROMACS-GUI
    ```

2.  安装依赖：
    ```bash
    pip install -r requirements.txt
    ```

### ⚙️ 配置

在运行之前，请务必配置您的 GROMACS 可执行文件路径。

打开 `src/core/config.py` 文件，修改 `GMX_PATH` 变量为您本地的 GROMACS 路径：

```python
# src/core/config.py

# 示例路径，请根据实际情况修改
GMX_PATH = r"C:\path\to\your\gmx.exe" 
```

### ▶️ 运行

在项目根目录下运行启动脚本：

**Windows:**
```bash
run.bat
```

**或者使用 Python 直接运行:**
```bash
python src/main.py
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！

## 📄 许可证

[MIT License](LICENSE)
