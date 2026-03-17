# GROMACS-GUI

这是一个基于 Python 和 PyQt6 开发的 GROMACS 图形用户界面 (GUI) 工具。旨在简化 GROMACS 分子动力学模拟的操作流程，提供可视化的参数配置和任务管理。

> **注意**: 本项目目前处于开发阶段 (Work In Progress)。

## ✨ 功能特性

目前主要模块为 **Solution Simulator** (溶液体系模拟)，支持以下完整流程：

1.  **拓扑与水箱 (Topology & Water Box)**
    *   生成拓扑文件
    *   定义溶剂盒子
2.  **能量最小化 (Energy Minimization)**
    *   **可视化 MDP 参数编辑器**: 支持图形化配置 integrator, nsteps, emtol 等关键参数
    *   运行能量最小化 (grompp & mdrun)
    *   实时日志输出
3.  **系统平衡 (System Equilibration)**
    *   **NVT 平衡**: 恒温模拟配置，支持温度耦合参数调整
    *   **NPT 平衡**: 恒压模拟配置，支持压力耦合参数调整
    *   集成 MDP 编辑器，轻松修改模拟参数
4.  **生产模拟 (Production MD)**
    *   配置长时间模拟参数 (md.mdp)
    *   执行正式分子动力学模拟
5.  **分析与可视化 (Analysis & Visualization)**
    *   **轨迹处理**: 运行 trjconv 去除周期性边界条件 (PBC)
    *   **数据分析与绘图**: 支持一键计算 RMSD, RMSF, Gyrate，并使用 Matplotlib 进行数据可视化
    *   **外部工具集成**: 预留 VMD 等可视化工具的启动接口

> **🚧 正在开发中的模块**:
> *   **Ligand Simulator**: 蛋白-配体复合物模拟 (WIP)
> *   **Membrane Simulator**: 膜蛋白体系模拟 (WIP)
> *   **Polymer Simulator**: 聚合物体系模拟 (WIP)


## 🛠️ 技术栈

*   **编程语言**: Python 3
*   **GUI 框架**: PyQt6
*   **数据可视化**: Matplotlib
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
