# GROMACS-GUI

[中文](./README.md) | [English](./README.en.md)

GROMACS-GUI 是一个基于 Python 与 PyQt6 的桌面工具，用于将常见的 GROMACS 分子动力学流程组织为更清晰的图形界面操作。

项目当前主要覆盖两类工作流：标准溶液体系模拟，以及蛋白-配体复合物体系构建与后续模拟。

## 项目概览

### Solution Simulator

面向常规溶液体系，当前支持以下流程：

- 拓扑生成与模拟盒定义
- 能量最小化
- NVT / NPT 平衡
- 生产模拟
- 轨迹处理与基础分析

其中能量最小化、平衡和生产阶段均提供 MDP 参数编辑能力；分析模块支持 `RMSD`、`RMSF`、`gyrate` 计算与绘图。

### Ligand Simulator

面向蛋白-配体复合物体系，当前支持以下流程：

- 导入外部工具生成的配体拓扑与结构文件，如 `CGenFF`、`ATB`、`ACPYPE`
- 受体蛋白 `pdb2gmx` 处理
- 蛋白与配体坐标合并
- `topol.top` 自动更新
- 溶剂化与离子添加
- 与后续 EM、EQ、MD、分析流程衔接

## 当前状态

当前已实现的核心模块：

- `Solution Simulator`
- `Ligand Simulator`

计划中的模块：

- `Membrane Simulator`
- `Polymer Simulator`

## 技术栈

- Python 3
- PyQt6
- Matplotlib
- GROMACS

## 安装

### 环境要求

1. 安装 Python 3.8 或更高版本
2. 安装可用的 GROMACS 环境

### 安装步骤

```bash
git clone https://github.com/JohnLei00001/GROMACS-GUI.git
cd GROMACS-GUI
pip install -r requirements.txt
```

## 配置

启动时会自动检测系统 PATH 中的 GROMACS。如未检测到，应用会弹出对话框引导选择 `gmx` 可执行文件路径。

也可随时通过界面上的「测试 GROMACS 环境」按钮重新配置。

如需手动指定，可编辑 [`src/core/config.py`](./src/core/config.py) 中的默认路径。

## 运行

Windows:

```bash
run.bat
```

Linux / macOS:

```bash
bash run.sh
```

或直接执行：

```bash
python src/main.py
```

## 反馈与贡献

欢迎通过 [Issues](https://github.com/JohnLei00001/GROMACS-GUI/issues) 提交使用中遇到的问题或功能建议。项目仍在持续完善。

## License

[MIT License](LICENSE)
